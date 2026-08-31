"""注册自定义 YOLO 模块（EMA / EMAAttention / ECA / SEAM / BiFPN / Residual）。"""
import math
import sys
import types
import torch
import torch.nn as nn
from collections import OrderedDict


class EMA(nn.Module):
    """EMA — Efficient Multi-Scale Attention (ICASSP 2023)。

    分组并行 1×1 + 3×3 卷积 → 跨空间学习 → 通道重标定。
    用于 best.pt（旧版改进模型），factor 默认 32。
    """

    def __init__(self, channels, factor=32):
        super().__init__()
        self.groups = factor
        assert channels // self.groups > 0
        self.softmax = nn.Softmax(-1)
        self.agp = nn.AdaptiveAvgPool2d((1, 1))
        self.pool_h = nn.AdaptiveAvgPool2d((None, 1))
        self.pool_w = nn.AdaptiveAvgPool2d((1, None))
        self.gn = nn.GroupNorm(channels // self.groups, channels // self.groups)
        self.conv1x1 = nn.Conv2d(channels // self.groups, channels // self.groups, 1, 1, 0)
        self.conv3x3 = nn.Conv2d(channels // self.groups, channels // self.groups, 3, 1, 1)

    def forward(self, x):
        b, c, h, w = x.size()
        group_x = x.reshape(b * self.groups, -1, h, w)
        x_h = self.pool_h(group_x)
        x_w = self.pool_w(group_x).permute(0, 1, 3, 2)
        hw = self.conv1x1(torch.cat([x_h, x_w], dim=2))
        x_h, x_w = torch.split(hw, [h, w], dim=2)
        x1 = self.gn(group_x * x_h.sigmoid() * x_w.permute(0, 1, 3, 2).sigmoid())
        x2 = self.conv3x3(group_x)
        x11 = self.softmax(self.agp(x1).reshape(b * self.groups, -1, 1).permute(0, 2, 1))
        x12 = x2.reshape(b * self.groups, c // self.groups, -1)
        x21 = self.softmax(self.agp(x2).reshape(b * self.groups, -1, 1).permute(0, 2, 1))
        x22 = x1.reshape(b * self.groups, c // self.groups, -1)
        weights = (torch.matmul(x11, x12) + torch.matmul(x21, x22)).reshape(b * self.groups, 1, h, w)
        return (group_x * weights.sigmoid()).reshape(b, c, h, w)


class EMAAttention(nn.Module):
    """EMAAttention — Efficient Multi-Scale Attention（新版，factor=8）。

    用于 fish_detect_s_ECA_EMA_BiFPN 模型。
    """

    def __init__(self, channels, factor=8):
        super().__init__()
        self.groups = factor
        c_per_g = channels // factor
        assert c_per_g > 0
        self.softmax = nn.Softmax(-1)
        self.agp = nn.AdaptiveAvgPool2d((1, 1))
        self.pool_h = nn.AdaptiveAvgPool2d((None, 1))
        self.pool_w = nn.AdaptiveAvgPool2d((1, None))
        self.gn = nn.GroupNorm(c_per_g, c_per_g)
        self.conv1x1 = nn.Conv2d(c_per_g, c_per_g, 1, 1, 0)
        self.conv3x3 = nn.Conv2d(c_per_g, c_per_g, 3, 1, 1)

    def forward(self, x):
        _, c, h, w = x.size()
        g = self.groups
        group_x = x.reshape(-1, c // g, h, w)
        x_h = self.pool_h(group_x)
        x_w = self.pool_w(group_x).permute(0, 1, 3, 2)
        hw = self.conv1x1(torch.cat([x_h, x_w], dim=2))
        x_h, x_w = torch.split(hw, [h, w], dim=2)
        x1 = self.gn(group_x * x_h.sigmoid() * x_w.permute(0, 1, 3, 2).sigmoid())
        x2 = self.conv3x3(group_x)
        n = x1.size(0)
        cpg = c // g
        x11 = self.softmax(self.agp(x1).reshape(n, -1, 1).permute(0, 2, 1))
        x12 = x2.reshape(n, cpg, -1)
        x21 = self.softmax(self.agp(x2).reshape(n, -1, 1).permute(0, 2, 1))
        x22 = x1.reshape(n, cpg, -1)
        weights = (torch.matmul(x11, x12) + torch.matmul(x21, x22)).reshape(n, 1, h, w)
        return (group_x * weights.sigmoid()).reshape(-1, c, h, w)


class ECAAttention(nn.Module):
    """ECA — Efficient Channel Attention (arXiv:1910.03151)。

    一维卷积自适应核大小 + Sigmoid 门控，轻量通道注意力。
    """

    def __init__(self, channels, b=1, gamma=2):
        super().__init__()
        kernel_size = int(abs((math.log(channels, 2) + b) / gamma))
        kernel_size = kernel_size if kernel_size % 2 else kernel_size + 1
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.conv = nn.Conv1d(1, 1, kernel_size=kernel_size, padding=(kernel_size - 1) // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        y = self.avg_pool(x)
        y = self.conv(y.squeeze(-1).transpose(-1, -2)).transpose(-1, -2).unsqueeze(-1)
        y = self.sigmoid(y)
        return x * y.expand_as(x)


class C2f_EMA(nn.Module):
    """C2f + EMA：在 C2f 输出端加入 EMA 注意力。"""

    def __init__(self, c1, c2, n=1, shortcut=False, g=1, e=0.5):
        super().__init__()
        from ultralytics.nn.modules.block import C2f
        self.c2f = C2f(c1, c2, n, shortcut, g, e)
        self.ema = EMA(c2)

    def forward(self, x):
        return self.ema(self.c2f(x))


class BiFPN_Concat(nn.Module):
    """BiFPN 加权特征融合（2 输入）。

    YAML 示例: [[-1, 9], 1, BiFPN_Concat, [1]]
    """

    def __init__(self, dimension=1):
        super().__init__()
        self.d = dimension
        self.w = nn.Parameter(torch.ones(2, dtype=torch.float32), requires_grad=True)
        self.epsilon = 0.0001

    def forward(self, x):
        w = torch.relu(self.w)
        weight = w / (torch.sum(w, dim=0) + self.epsilon)
        return weight[0] * x[0] + weight[1] * x[1]


class BiFPN_Concat_3(nn.Module):
    """BiFPN 加权特征融合（3 输入）。

    YAML 示例: [[-1, 19, 6], 1, BiFPN_Concat_3, [1]]
    """

    def __init__(self, dimension=1):
        super().__init__()
        self.d = dimension
        self.w = nn.Parameter(torch.ones(3, dtype=torch.float32), requires_grad=True)
        self.epsilon = 0.0001

    def forward(self, x):
        w = torch.relu(self.w)
        weight = w / (torch.sum(w, dim=0) + self.epsilon)
        return weight[0] * x[0] + weight[1] * x[1] + weight[2] * x[2]


class Residual(nn.Module):
    """真残差块：output = x + f(x)，用于 SEAM 内部深度可分离卷积的残差连接。"""
    def __init__(self, module):
        super().__init__()
        self.module = module

    def forward(self, x):
        return x + self.module(x)


class SEAM(nn.Module):
    """SEAM 空间增强注意力模块（YOLO-FaceV2 提出）。

    forward: x → DCovN → avg_pool → fc → sigmoid → exp → x * weight
    指数变换增强通道注意力的区分度。
    """

    def __init__(self, c1, c2=None, n=1, reduction=16, **kwargs):
        super().__init__()
        if c2 is not None and c2 != c1:
            c2 = c1
        else:
            c2 = c1

        self._args = dict(c1=c1, n=n, reduction=reduction)
        if c1 > 0:
            self._build(c1, c2, n, reduction)

    def _build(self, c1, c2, n, reduction):
        # DCovN: 深度可分离卷积 + 残差堆叠，n 控制深度
        blocks = []
        for _ in range(n):
            blocks.append(OrderedDict([
                ("0", Residual(nn.Sequential(OrderedDict([
                    ("0", nn.Conv2d(c2, c2, 3, 1, 1, groups=c2)),
                    ("1", nn.GELU()),
                    ("2", nn.BatchNorm2d(c2)),
                ])))),
                ("1", nn.Conv2d(c2, c2, 1, 1, 0)),
                ("2", nn.GELU()),
                ("3", nn.BatchNorm2d(c2)),
            ]))
        if len(blocks) == 1:
            self.DCovN = nn.Sequential(blocks[0])
        else:
            # 多块时包装为 Sequential of Sequential
            self.DCovN = nn.Sequential(OrderedDict([
                (str(i), nn.Sequential(block)) for i, block in enumerate(blocks)
            ]))

        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(OrderedDict([
            ("0", nn.Linear(c2, c2 // reduction, bias=False)),
            ("1", nn.ReLU(inplace=True)),
            ("2", nn.Linear(c2 // reduction, c2, bias=False)),
            ("3", nn.Sigmoid()),
        ]))

        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.xavier_uniform_(m.weight, gain=1)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
        # fc 层用正态初始化
        for layer in [self.fc]:
            if isinstance(layer, (nn.Conv2d, nn.Linear)):
                torch.nn.init.normal_(layer.weight, mean=0., std=0.001)
                if layer.bias is not None:
                    torch.nn.init.constant_(layer.bias, 0)

    def _load_from_state_dict(self, state_dict, prefix, local_metadata, strict,
                              missing_keys, unexpected_keys, error_msgs):
        if not hasattr(self, 'DCovN'):
            key = prefix + 'fc.0.weight'
            if key in state_dict:
                c2 = int(state_dict[key].shape[1])
                reduction_ratio = c2 // state_dict[key].shape[0]
                key2 = prefix + 'fc.2.weight'
                if key2 in state_dict:
                    c2 = int(state_dict[key2].shape[0])
                self._build(c1=c2, c2=c2, n=self._args.get('n', 1),
                            reduction=reduction_ratio)
        super()._load_from_state_dict(state_dict, prefix, local_metadata, strict,
                                       missing_keys, unexpected_keys, error_msgs)

    def forward(self, x):
        b, c, _, _ = x.size()
        y = self.DCovN(x)
        y = self.avg_pool(y).view(b, c)
        y = self.fc(y).view(b, c, 1, 1)
        y = torch.exp(y)
        return x * y.expand_as(x)


def _mkmod(name, **classes):
    """创建假模块并注入 sys.modules，返回模块对象。"""
    m = types.ModuleType(name)
    for k, v in classes.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


def register():
    # SEAM / Residual
    _mkmod("ultralytics.nn.modules.SEAM", SEAM=SEAM, Residual=Residual)

    # 注意力模块
    _mkmod("ultralytics.nn.modules.attention",
           EMA=EMA, C2f_EMA=C2f_EMA,
           EMAAttention=EMAAttention, ECAAttention=ECAAttention)

    # 训练时使用的自定义模块路径（兼容 fish_detect_s_ECA_EMA_BiFPN.pt）
    _modules_pkg = _mkmod("modules", __path__=[])
    _ema_attn = _mkmod("modules.ema_attention", EMAAttention=EMAAttention, ECAAttention=ECAAttention)
    _eca_attn = _mkmod("modules.eca_attention", ECAAttention=ECAAttention)
    _bifpn = _mkmod("modules.bifpn", BiFPN_Concat=BiFPN_Concat, BiFPN_Concat_3=BiFPN_Concat_3)
    _modules_pkg.ema_attention = _ema_attn
    _modules_pkg.eca_attention = _eca_attn
    _modules_pkg.bifpn = _bifpn

    # BiFPN
    _mkmod("ultralytics.nn.modules.bifpn",
           BiFPN_Concat=BiFPN_Concat, BiFPN_Concat_3=BiFPN_Concat_3)
