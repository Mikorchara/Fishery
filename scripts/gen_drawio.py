"""Generate drawio files with edges that survive the linter."""
import os

def make_edge(id_, x1, y1, x2, y2, style):
    return ('        <mxCell id="{}" value="" style="{}" edge="1" parent="1">\n'
            '          <mxGeometry relative="1" as="geometry">\n'
            '            <mxPoint x="{}" y="{}" as="sourcePoint"/>\n'
            '            <mxPoint x="{}" y="{}" as="targetPoint"/>\n'
            '          </mxGeometry>\n'
            '        </mxCell>').format(id_, style, x1, y1, x2, y2)

def make_vertex(id_, x, y, w, h, value, style):
    return ('        <mxCell id="{}" value="{}" style="{}" vertex="1" parent="1">\n'
            '          <mxGeometry x="{}" y="{}" width="{}" height="{}" as="geometry"/>\n'
            '        </mxCell>').format(id_, value, style, x, y, w, h)

def header(title, w, h):
    return ('<mxGraphModel dx="1400" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" '
            'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{}" pageHeight="{}" '
            'math="0" shadow="0">\n'
            '  <root>\n'
            '    <mxCell id="0"/>\n'
            '    <mxCell id="1" parent="0"/>\n'
            '    <mxCell id="title" value="{}" style="text;fontSize=15;fontFamily=宋体;fontStyle=1;align=center;" vertex="1" parent="1">\n'
            '      <mxGeometry x="200" y="10" width="500" height="30" as="geometry"/>\n'
            '    </mxCell>').format(w, h, title)

footer = '  </root>\n</mxGraphModel>'

d = r'F:\onedrive\graduation\Fishery_Project\thesis-ai-standard\drawio'
S = "fontSize=11;fontFamily=宋体"

# =============================================
# figure-3-4-frame-sequence
# =============================================
lines = [header("图3-4 视频帧处理流水线时序图", 1400, 950)]

# Participants
verts = [
    ("h0", 15, 55, 85, 42, "RTSP&#xa;摄像头", "rounded=1;whiteSpace=wrap;fillColor=#E8D5F5;strokeColor=#7B2D8E;strokeWidth=2;{};fontStyle=1".format(S)),
    ("h1", 155, 55, 100, 42, "VideoCapture&#xa;Threading", "rounded=1;whiteSpace=wrap;fillColor=#D0E4FF;strokeColor=#1A56DB;strokeWidth=2;{};fontStyle=1".format(S)),
    ("h2", 310, 55, 100, 42, "WWEEnhancer", "rounded=1;whiteSpace=wrap;fillColor=#FFF8CC;strokeColor=#B8860B;strokeWidth=2;{};fontStyle=1".format(S)),
    ("h3", 465, 55, 100, 42, "FisheryAI", "rounded=1;whiteSpace=wrap;fillColor=#D5F0D5;strokeColor=#1A7A1A;strokeWidth=2;{};fontStyle=1".format(S)),
    ("h4", 620, 55, 105, 42, "FrameProcessor", "rounded=1;whiteSpace=wrap;fillColor=#FFE0D0;strokeColor=#C03020;strokeWidth=2;{};fontStyle=1".format(S)),
    ("h5", 780, 55, 80, 42, "MJPEG推流", "rounded=1;whiteSpace=wrap;fillColor=#D0E4FF;strokeColor=#1A56DB;strokeWidth=2;{};fontStyle=1".format(S)),
    ("h6", 915, 55, 95, 42, "H.264 WS推流", "rounded=1;whiteSpace=wrap;fillColor=#D5F0D5;strokeColor=#1A7A1A;strokeWidth=2;{};fontStyle=1".format(S)),
    ("h7", 1090, 55, 80, 42, "浏览器", "rounded=1;whiteSpace=wrap;fillColor=#E8D5F5;strokeColor=#7B2D8E;strokeWidth=2;{};fontStyle=1".format(S)),
]
for v in verts:
    lines.append(make_vertex(*v))

# Lifelines
xs = [57, 205, 360, 515, 672, 820, 962, 1130]
cs = ["#7B2D8E", "#1A56DB", "#B8860B", "#1A7A1A", "#C03020", "#1A56DB", "#1A7A1A", "#7B2D8E"]
for i, (x, c) in enumerate(zip(xs, cs)):
    lines.append(make_edge("L{}".format(i), x, 110, x, 900, "endArrow=none;dashed=1;strokeWidth=2;dashPattern=8 4;strokeColor={}".format(c)))

# Step edges
lines.append(make_edge("A1", 57, 220, 205, 220, "endArrow=block;strokeWidth=3;strokeColor=#1A56DB"))
lines.append(make_vertex("T1", 75, 198, 230, 18, "1. read() 获取最新BGR帧（非阻塞）", "text;fontSize=11;fontFamily=宋体;fontColor=#1A56DB;fontStyle=1"))
lines.append(make_edge("A2", 205, 290, 360, 290, "endArrow=block;strokeWidth=3;strokeColor=#B8860B"))
lines.append(make_vertex("T2", 215, 268, 220, 18, "2. enhance(frame) 水下图像增强 [可选]", "text;fontSize=11;fontFamily=宋体;fontColor=#B8860B;fontStyle=1"))
lines.append(make_edge("A2b", 360, 318, 205, 318, "endArrow=open;strokeWidth=2;strokeColor=#B8860B;dashed=1"))
lines.append(make_edge("A2s", 205, 348, 515, 348, "endArrow=open;strokeWidth=1;strokeColor=#AAAAAA;dashed=1"))
lines.append(make_vertex("T2s", 330, 343, 60, 14, "OFF->跳过", "text;fontSize=9;fontFamily=宋体;fontColor=#AAAAAA"))
lines.append(make_edge("A3", 205, 420, 515, 420, "endArrow=block;strokeWidth=3;strokeColor=#1A7A1A"))
lines.append(make_vertex("T3", 215, 398, 280, 18, "3. process_frame(frame, seg_enabled) AI推理 [可选]", "text;fontSize=11;fontFamily=宋体;fontColor=#1A7A1A;fontStyle=1"))
for j, (y, txt) in enumerate([(440, "3a. YOLO模型检测 --> boxes[] + confs"), (458, "3b. 分割ON --> SAM2点提示或YOLO-seg直出掩码"), (476, "3c. MaskTracker帧间IoU追踪、分配ID"), (494, "3d. GPU端plot()渲染检测框和掩码")]):
    lines.append(make_vertex("T3{}".format(j), 530, y, 230, 14, txt, "text;fontSize=9;fontFamily=宋体;fontColor=#1A7A1A"))
lines.append(make_edge("A3b", 515, 558, 205, 558, "endArrow=open;strokeWidth=2;strokeColor=#1A7A1A;dashed=1"))
lines.append(make_edge("A3s", 205, 608, 672, 608, "endArrow=open;strokeWidth=1;strokeColor=#AAAAAA;dashed=1"))
lines.append(make_vertex("T3s", 400, 603, 90, 14, "OFF->frame.copy()", "text;fontSize=9;fontFamily=宋体;fontColor=#AAAAAA"))
lines.append(make_edge("A4", 205, 670, 672, 670, "endArrow=block;strokeWidth=3;strokeColor=#C03020"))
lines.append(make_vertex("T4", 290, 648, 300, 18, "4. FPS叠加(黄色) + 鱼群计数(绿色) + 录制副本", "text;fontSize=11;fontFamily=宋体;fontColor=#C03020;fontStyle=1"))
lines.append(make_vertex("fork", 678, 728, 55, 22, "两路并发", "rounded=1;fillColor=#F0F0F0;strokeColor=#666666;fontSize=10;fontFamily=宋体"))
lines.append(make_edge("A5", 672, 760, 820, 760, "endArrow=block;strokeWidth=3;strokeColor=#1A56DB"))
lines.append(make_vertex("T5", 690, 738, 220, 18, "5. cv2.imencode('.jpg') --> multipart封装", "text;fontSize=11;fontFamily=宋体;fontColor=#1A56DB;fontStyle=1"))
lines.append(make_edge("A6", 672, 795, 962, 795, "endArrow=block;strokeWidth=3;strokeColor=#1A7A1A"))
lines.append(make_vertex("T6", 720, 773, 210, 18, "6. FFmpeg libx264编码 --> fMP4媒体段", "text;fontSize=11;fontFamily=宋体;fontColor=#1A7A1A;fontStyle=1"))
lines.append(make_edge("A7", 820, 843, 1130, 843, "endArrow=block;strokeWidth=3;strokeColor=#1A56DB"))
lines.append(make_vertex("T7", 870, 823, 220, 18, "7. HTTP响应 --> img标签 (保底方案)", "text;fontSize=11;fontFamily=宋体;fontColor=#1A56DB;fontStyle=1"))
lines.append(make_edge("A8", 962, 878, 1130, 878, "endArrow=block;strokeWidth=3;strokeColor=#1A7A1A"))
lines.append(make_vertex("T8", 975, 858, 230, 18, "8. WebSocket推送 --> MSE video (高清)", "text;fontSize=11;fontFamily=宋体;fontColor=#1A7A1A;fontStyle=1"))

lines.append(footer)
with open(os.path.join(d, 'figure-3-4-frame-sequence.drawio'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('figure-3-4: done')

# =============================================
# figure-3-x-frame-algorithm
# =============================================
lines = [header("图3-X 视频帧处理算法流程", 900, 1200)]
lines.append(make_vertex("start", 380, 50, 100, 40, "开始", "ellipse;fillColor=#D5F0D5;strokeColor=#1A7A1A;strokeWidth=2;{};fontStyle=1".format(S)))
lines.append(make_vertex("read", 340, 110, 180, 50, "video_stream.read()&#xa;获取最新帧", "rounded=1;fillColor=#D0E4FF;strokeColor=#1A56DB;strokeWidth=2;{}".format(S)))
lines.append(make_edge("e1", 430, 90, 430, 110, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_vertex("ret", 350, 180, 160, 85, "ret == True?", "rhombus;fillColor=#FFF8CC;strokeColor=#B8860B;strokeWidth=2;{}".format(S)))
lines.append(make_edge("e2", 430, 160, 430, 180, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_vertex("rfail", 540, 205, 110, 35, "sleep(10ms)", "rounded=1;fillColor=#FFE0D0;strokeColor=#C03020;strokeWidth=2;fontSize=10;fontFamily=宋体"))
lines.append(make_edge("e2f", 510, 222, 540, 222, "endArrow=block;strokeWidth=1.5;strokeColor=#C03020"))
lines.append(make_vertex("e2l", 480, 212, 25, 14, "否", "text;fontSize=10;fontFamily=宋体;fontColor=#C03020"))
lines.append(make_vertex("enh", 350, 290, 160, 85, "增强开关已启用?", "rhombus;fillColor=#FFF8CC;strokeColor=#B8860B;strokeWidth=2;{}".format(S)))
lines.append(make_edge("e3", 430, 265, 430, 290, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_vertex("doenh", 540, 305, 200, 55, "enhancer.enhance(frame)&#xa;BGR->RGB->WWE-UIE->RGB->BGR", "rounded=1;fillColor=#FFF8CC;strokeColor=#B8860B;strokeWidth=2;fontSize=10;fontFamily=宋体"))
lines.append(make_edge("e3y", 510, 332, 540, 332, "endArrow=block;strokeWidth=1.5;strokeColor=#B8860B"))
lines.append(make_vertex("e3l", 480, 322, 25, 14, "是", "text;fontSize=10;fontFamily=宋体;fontColor=#B8860B"))
lines.append(make_vertex("ai", 350, 400, 160, 85, "AI 开关已启用?", "rhombus;fillColor=#FFF8CC;strokeColor=#1A7A1A;strokeWidth=2;{}".format(S)))
lines.append(make_edge("e4", 430, 375, 430, 400, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_edge("e3m", 640, 360, 430, 400, "endArrow=block;strokeWidth=1.5;strokeColor=#333333"))
lines.append(make_vertex("doai", 540, 405, 210, 60, "ai_detector.process_frame(frame, seg_enabled)", "rounded=1;fillColor=#D5F0D5;strokeColor=#1A7A1A;strokeWidth=2;fontSize=10;fontFamily=宋体"))
lines.append(make_edge("e4y", 510, 442, 540, 442, "endArrow=block;strokeWidth=1.5;strokeColor=#1A7A1A"))
lines.append(make_vertex("e4l", 480, 432, 25, 14, "是", "text;fontSize=10;fontFamily=宋体;fontColor=#1A7A1A"))
lines.append(make_vertex("sub", 520, 475, 210, 125, "", "rounded=1;fillColor=none;strokeColor=#1A7A1A;strokeWidth=1;dashed=1;dashPattern=6 4"))
lines.append(make_vertex("subt", 530, 480, 190, 110, "YOLO detect -> boxes[]&#xa;seg_enabled?&#xa;  YOLO-seg: 直出掩码&#xa;  fish_detect: SAM2点提示分割&#xa;MaskTracker IoU追踪&#xa;plot() 渲染标注帧", "text;fontSize=9;fontFamily=宋体;fontColor=#333333;align=left"))
lines.append(make_edge("e4s", 645, 465, 645, 475, "endArrow=block;strokeWidth=1.5;strokeColor=#1A7A1A"))
lines.append(make_vertex("fps", 340, 630, 180, 40, "叠加 FPS 和鱼群计数", "rounded=1;fillColor=#FFE0D0;strokeColor=#C03020;strokeWidth=2;{}".format(S)))
lines.append(make_edge("e5", 430, 480, 430, 630, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_edge("e4m", 645, 600, 520, 630, "endArrow=block;strokeWidth=1.5;strokeColor=#333333"))
lines.append(make_vertex("strm", 340, 695, 180, 80, "推流方式?", "rhombus;fillColor=#D0E4FF;strokeColor=#1A56DB;strokeWidth=2;{}".format(S)))
lines.append(make_edge("e6", 430, 670, 430, 695, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_vertex("mj", 150, 705, 160, 50, "cv2.imencode('.jpg')&#xa;multipart封装->HTTP", "rounded=1;fillColor=#D0E4FF;strokeColor=#1A56DB;strokeWidth=2;fontSize=10;fontFamily=宋体"))
lines.append(make_edge("e6m", 340, 730, 310, 730, "endArrow=block;strokeWidth=1.5;strokeColor=#1A56DB"))
lines.append(make_vertex("e6ml", 295, 715, 45, 14, "MJPEG", "text;fontSize=10;fontFamily=宋体;fontColor=#1A56DB"))
lines.append(make_vertex("h264", 540, 705, 170, 50, "FFmpeg libx264编码&#xa;fMP4段->WebSocket", "rounded=1;fillColor=#D5F0D5;strokeColor=#1A7A1A;strokeWidth=2;fontSize=10;fontFamily=宋体"))
lines.append(make_edge("e6h", 520, 730, 540, 730, "endArrow=block;strokeWidth=1.5;strokeColor=#1A7A1A"))
lines.append(make_vertex("e6hl", 485, 715, 45, 14, "H.264", "text;fontSize=10;fontFamily=宋体;fontColor=#1A7A1A"))
lines.append(make_vertex("out", 340, 790, 180, 40, "浏览器接收并播放", "rounded=1;fillColor=#E8D5F5;strokeColor=#7B2D8E;strokeWidth=2;{};fontStyle=1".format(S)))
lines.append(make_edge("e7m", 230, 755, 340, 810, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_edge("e7h", 625, 755, 520, 810, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_edge("loop", 430, 830, 430, 135, "endArrow=block;strokeWidth=2;strokeColor=#C03020;dashed=1"))
lines.append(make_vertex("loopl", 435, 620, 35, 30, "循环下一帧", "text;fontSize=10;fontFamily=宋体;fontColor=#C03020;fontStyle=2"))
lines.append(footer)
with open(os.path.join(d, 'figure-3-x-frame-algorithm.drawio'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('figure-3-x-frame-algorithm: done')

# =============================================
# figure-3-x-backoff-algorithm
# =============================================
lines = [header("图3-X 指数退避断线重连算法流程", 700, 600)]
lines.append(make_vertex("start", 270, 50, 120, 40, "后台线程开始", "ellipse;fillColor=#D5F0D5;strokeColor=#1A7A1A;strokeWidth=2;fontSize=12;fontFamily=宋体;fontStyle=1"))
lines.append(make_vertex("init", 230, 110, 200, 42, "n=0, T0=0.5s, Tmax=10s", "rounded=1;fillColor=#D0E4FF;strokeColor=#1A56DB;strokeWidth=2;{}".format(S)))
lines.append(make_edge("b1", 330, 90, 330, 110, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_vertex("read", 255, 175, 150, 42, "cap.read() 读取帧", "rounded=1;fillColor=#D0E4FF;strokeColor=#1A56DB;strokeWidth=2;{}".format(S)))
lines.append(make_edge("b2", 330, 152, 330, 175, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_vertex("cond", 270, 240, 120, 75, "ret == True?", "rhombus;fillColor=#FFF8CC;strokeColor=#B8860B;strokeWidth=2;{}".format(S)))
lines.append(make_edge("b3", 330, 217, 330, 240, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_vertex("ok", 150, 260, 105, 50, "n=0重置等待&#xa;更新帧缓冲", "rounded=1;fillColor=#D5F0D5;strokeColor=#1A7A1A;strokeWidth=2;fontSize=10;fontFamily=宋体"))
lines.append(make_edge("b3y", 270, 277, 255, 277, "endArrow=block;strokeWidth=1.5;strokeColor=#333333"))
lines.append(make_vertex("b3l", 240, 267, 25, 14, "是", "text;fontSize=10;fontFamily=宋体;fontColor=#1A7A1A"))
lines.append(make_edge("b3b", 200, 285, 200, 196, "endArrow=block;strokeWidth=1.5;strokeColor=#1A7A1A;dashed=1"))
lines.append(make_vertex("fail", 410, 250, 190, 65, "Twait=min(T0*2^n,Tmax)&#xa;n=n+1", "rounded=1;fillColor=#FFE0D0;strokeColor=#C03020;strokeWidth=2;fontSize=10;fontFamily=宋体;align=left"))
lines.append(make_edge("b3n", 390, 280, 410, 280, "endArrow=block;strokeWidth=1.5;strokeColor=#333333"))
lines.append(make_vertex("b3nl", 370, 270, 25, 14, "否", "text;fontSize=10;fontFamily=宋体;fontColor=#C03020"))
lines.append(make_vertex("sleep", 440, 340, 110, 38, "sleep(Twait)", "rounded=1;fillColor=#FFE0D0;strokeColor=#C03020;strokeWidth=2;{}".format(S)))
lines.append(make_edge("b4", 505, 315, 505, 340, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_vertex("recon", 440, 400, 130, 42, "重新初始化RTSP连接", "rounded=1;fillColor=#D0E4FF;strokeColor=#1A56DB;strokeWidth=2;fontSize=10;fontFamily=宋体"))
lines.append(make_edge("b5", 505, 378, 505, 400, "endArrow=block;strokeWidth=2;strokeColor=#333333"))
lines.append(make_vertex("form", 180, 370, 220, 55, "Twait(n)=min(T0*2^n, Tmax)&#xa;T0=0.5s,Tmax=10s&#xa;重连成功后n清零", "text;fontSize=10;fontFamily=宋体;fontColor=#333333;fontStyle=2;align=left;strokeColor=#999999;strokeWidth=1;rounded=1;fillColor=#F5F5F5"))
lines.append(footer)
with open(os.path.join(d, 'figure-3-x-backoff-algorithm.drawio'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('figure-3-x-backoff-algorithm: done')
print('All regenerated.')
