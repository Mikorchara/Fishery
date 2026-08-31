"""Fine-tune WWE-UIE 增强模型，用你自己的 paired 数据。

数据目录结构：
  水下/paired/
  ├── trainA/  原始水下图片
  ├── trainB/  增强后的参照图
  ├── valA/    验证原始图
  └── valB/    验证参照图

用法：
  python scripts/finetune_enhancer.py --data "F:\onedrive\graduation\跟踪数据集\水下\paired" --epochs 50
"""
import sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from PIL import Image, ImageOps
from torchvision.transforms import ToTensor
import random
import argparse

# 加载现有增强器和模型定义
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "WWE-UIE"))
from model import myModel
from utils.loss_funcs import L1_Charbonnier_loss, SSIMLoss, PerceptualLoss, EdgeAwareLoss


class PairedDataset(Dataset):
    """简单的成对图片 Dataset: trainA/ ←原始, trainB/ ←参照。"""
    def __init__(self, root, data_size=256, train=True):
        folder_a = os.path.join(root, "trainA" if train else "valA")
        folder_b = os.path.join(root, "trainB" if train else "valB")
        exts = {".jpg", ".jpeg", ".png", ".bmp"}
        files = sorted([f for f in os.listdir(folder_a) if os.path.splitext(f)[1].lower() in exts])
        self.pairs = []
        for f in files:
            pa = os.path.join(folder_a, f)
            pb = os.path.join(folder_b, f)
            if os.path.exists(pb):
                self.pairs.append((pa, pb))
        self.data_size = data_size
        self.train = train
        self.transform = ToTensor()

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        pa, pb = self.pairs[idx]
        inp = Image.open(pa).convert("RGB")
        tgt = Image.open(pb).convert("RGB")

        # 统一 resize 到 data_size
        inp = inp.resize((self.data_size, self.data_size), Image.BILINEAR)
        tgt = tgt.resize((self.data_size, self.data_size), Image.BILINEAR)

        if self.train:
            # 随机水平/垂直翻转
            if random.random() < 0.5:
                inp = ImageOps.flip(inp)
                tgt = ImageOps.flip(tgt)
            if random.random() < 0.5:
                inp = ImageOps.mirror(inp)
                tgt = ImageOps.mirror(tgt)

        return self.transform(inp), self.transform(tgt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="paired 数据根目录 (含 trainA/trainB/valA/valB)")
    parser.add_argument("--epochs", type=int, default=50, help="训练轮数")
    parser.add_argument("--lr", type=float, default=1e-5, help="学习率 (fine-tune 用小 LR)")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--save", default="", help="输出权重路径，默认自动生成")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"设备: {device}")

    # 1. 加载预训练模型
    print("加载预训练 WWE-UIE 模型...")
    model = myModel(in_channels=3, feature_channels=32, use_white_balance=True).to(device)

    # 自动找 best_model.pth
    wwe_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "WWE-UIE")
    output_dir = os.path.join(wwe_dir, "output", "Fishery_WWE_UIEB", "UIEB")
    weight_path = None
    if os.path.exists(output_dir):
        subdirs = sorted([d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))])
        if subdirs:
            pth = os.path.join(output_dir, subdirs[-1], "best_model.pth")
            if os.path.exists(pth):
                weight_path = pth
    if weight_path:
        print(f"  权重: {weight_path}")
        ckpt = torch.load(weight_path, map_location=device)
        model.load_state_dict(ckpt, strict=False)
    else:
        print("  ⚠ 未找到预训练权重，将从随机初始化开始训练")

    # 保持 FP32 训练，用 autocast 做混合精度

    # 2. 数据
    train_set = PairedDataset(args.data, data_size=256, train=True)
    val_set = PairedDataset(args.data, data_size=256, train=False)
    print(f"训练集: {len(train_set)} 对, 验证集: {len(val_set)} 对")

    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True,
                              num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False,
                            num_workers=0, pin_memory=True)

    # 3. 优化器 & 损失
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, args.epochs, eta_min=args.lr * 1e-3)

    l1_loss = L1_Charbonnier_loss()
    ssim_loss_fn = SSIMLoss(device=str(device), window_size=5)
    edge_loss_fn = EdgeAwareLoss(loss_type="l2", device=str(device))

    # 4. 输出路径
    if not args.save:
        args.save = os.path.join(os.path.dirname(args.data), "finetune_output", "best_finetune.pth")
    os.makedirs(os.path.dirname(args.save), exist_ok=True)

    # 5. 训练
    best_val_loss = float("inf")
    use_amp = device.type == "cuda"

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        t0 = time.time()

        for inp, tgt in train_loader:
            inp = inp.to(device)
            tgt = tgt.to(device)

            optimizer.zero_grad()

            with torch.amp.autocast("cuda") if use_amp else torch.no_grad():
                pred = model(inp)
                loss = l1_loss(pred, tgt) + 0.1 * ssim_loss_fn(pred, tgt) + 0.1 * edge_loss_fn(pred, tgt)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        scheduler.step()
        train_loss /= len(train_loader)

        # 验证
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for inp, tgt in val_loader:
                inp, tgt = inp.to(device), tgt.to(device)
                with torch.amp.autocast("cuda") if use_amp else torch.no_grad():
                    pred = model(inp)
                    val_loss += l1_loss(pred, tgt).item()
        val_loss /= len(val_loader)

        elapsed = time.time() - t0
        print(f"[{epoch:3d}/{args.epochs}] train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  "
              f"lr={scheduler.get_last_lr()[0]:.2e}  {elapsed:.0f}s")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), args.save)
            print(f"  → 保存最佳模型: {args.save}")

    print(f"\n完成! 最佳模型: {args.save}")


if __name__ == "__main__":
    main()
