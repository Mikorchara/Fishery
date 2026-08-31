<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>智慧渔业水下协同控制系统</title>
    <!-- 引入 Marked.js 用于渲染 AI 返回的 Markdown -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        /* 定义全局 CSS 变量 */
        :root { 
            --bg-color: #f1f5f9; 
            --panel-bg: #ffffff; 
            --text-main: #1e293b; 
            --text-muted: #64748b; 
            --accent: #334155; 
            --success: #16a34a; 
            --danger: #dc2626; 
            --border-color: #e2e8f0;
            --ai-bubble: #f8fafc;
            --user-bubble: #eff6ff;
        }
        
        * { box-sizing: border-box; }

        body { 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
            background-color: var(--bg-color); 
            color: var(--text-main); 
            margin: 0; 
            padding: 10px 15px; 
            display: flex; 
            flex-direction: column; 
            height: 100vh; 
            overflow: hidden; 
        }
        
        header { 
            display: flex; justify-content: space-between; align-items: center; 
            padding-bottom: 8px; border-bottom: 1px solid var(--border-color); margin-bottom: 10px; 
        }
        h1 { margin: 0; font-size: 18px; color: var(--accent); font-weight: 600; }
        
        .dashboard { display: flex; gap: 0; flex: 1; min-height: 0; }

        .resize-handle {
            width: 6px; cursor: col-resize; flex-shrink: 0;
            background: var(--border-color); transition: background 0.15s;
            border-radius: 3px; margin: 0 6px; align-self: stretch;
        }
        .resize-handle:hover, .resize-handle.active { background: #2563eb; }
        
        .video-section {
            flex: 1 1 0; min-width: 300px; overflow: hidden;
            background: var(--panel-bg); border-radius: 6px; padding: 10px;
            display: flex; flex-direction: column; border: 1px solid var(--border-color);
            min-height: 0;
        }
        .video-header { 
            margin-bottom: 8px; font-weight: 500; color: var(--text-main); 
            display: flex; justify-content: space-between; font-size: 13px; 
        }
        .video-wrapper { 
            flex: 1; background: #000; border-radius: 4px; overflow: hidden; 
            position: relative; display: flex; justify-content: center; align-items: center; 
            border: 1px solid var(--border-color);
        }
        .video-wrapper img { max-width: 100%; max-height: 100%; object-fit: contain; }
        
        .side-panel {
            flex: 0 0 420px; display: flex; flex-direction: column; gap: 8px;
            min-width: 320px; max-width: 700px; overflow-y: auto; padding-right: 5px;
        }
        
        .card {
            background: var(--panel-bg); border-radius: 6px; padding: 10px;
            border: 1px solid var(--border-color);
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .card h3 {
            margin-top: 0; color: var(--text-main); font-size: 13px; font-weight: 600;
            margin-bottom: 6px; border-left: 3px solid var(--accent); padding-left: 8px;
        }
        
        button { 
            width: 100%; padding: 8px; font-size: 12px; font-weight: 500; 
            border: 1px solid var(--border-color); border-radius: 4px; cursor: pointer; transition: all 0.2s ease; 
            display: flex; justify-content: center; align-items: center; gap: 6px; background: #fff;
        }
        .btn-on { color: var(--success); border-color: var(--success); background-color: #f0fdf4; }
        .btn-off { color: var(--text-muted); border-color: var(--border-color); background-color: #f8fafc; }
        
        select { 
            width: 100%; padding: 6px; background: #fff; color: var(--text-main); 
            border: 1px solid var(--border-color); border-radius: 4px; font-size: 12px; 
        }

        .sensor-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
        .sensor-item { 
            background: #f8fafc; border: 1px solid var(--border-color); 
            padding: 8px; border-radius: 4px; text-align: center;
        }
        .sensor-label { font-size: 10px; color: var(--text-muted); margin-bottom: 2px; }
        .sensor-value { font-size: 15px; font-weight: 600; color: var(--accent); font-family: monospace; }
        .sensor-unit { font-size: 10px; margin-left: 1px; }

        /* AI 对话窗口样式重构 */
        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
            background: #fff;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            margin-top: 5px;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: #fafafa;
        }
        .msg {
            max-width: 85%;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            line-height: 1.5;
            word-wrap: break-word;
        }
        .msg-ai {
            align-self: flex-start;
            background-color: var(--ai-bubble);
            border: 1px solid var(--border-color);
            color: #334155;
        }
        .msg-user {
            align-self: flex-end;
            background-color: #2563eb;
            color: white;
        }
        .msg-ai h1, .msg-ai h2, .msg-ai h3 { font-size: 13px; margin: 5px 0; }
        .msg-ai p { margin: 5px 0; }

        .chat-input-area {
            display: flex;
            padding: 8px;
            gap: 8px;
            background: #fff;
            border-top: 1px solid var(--border-color);
        }
        .chat-input-area input {
            flex: 1;
            padding: 8px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 12px;
            outline: none;
        }
        .chat-input-area input:focus { border-color: #2563eb; }
        .send-btn {
            width: auto; padding: 0 15px; background: #2563eb; color: white; border: none;
        }
        .capture-btn {
            width: auto; padding: 4px 12px; font-size: 11px; cursor: pointer;
            background: #fff; border: 1px solid var(--border-color); border-radius: 4px;
            color: var(--text-main); transition: all 0.2s;
        }
        .capture-btn:hover { background: #f0fdf4; border-color: var(--success); color: var(--success); }
        .capture-btn:active { transform: scale(0.95); }
        .capture-toast {
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
            background: #16a34a; color: #fff; padding: 8px 20px; border-radius: 6px;
            font-size: 13px; z-index: 999; pointer-events: none; opacity: 0;
            transition: opacity 0.3s;
        }
        .capture-toast.show { opacity: 1; }

        .alarm-banner {
            display: none; align-items: center; gap: 8px;
            padding: 8px 15px; font-size: 13px; font-weight: 500;
            border-radius: 4px; margin-bottom: 6px; animation: alarmPulse 2s infinite;
        }
        .alarm-banner.warning { display: flex; background: #fffbeb; border: 1px solid #f59e0b; color: #b45309; }
        .alarm-banner.critical { display: flex; background: #fef2f2; border: 1px solid #dc2626; color: #991b1b; }
        @keyframes alarmPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .alarm-badge {
            font-size: 10px; padding: 2px 6px; border-radius: 10px; color: #fff;
        }
        .alarm-badge.warning { background: #f59e0b; }
        .alarm-badge.critical { background: #dc2626; }

        .chart-wrap { margin-top: 8px; position: relative; }
        .chart-wrap canvas { width: 100%; height: 80px; display: block; border-radius: 4px; background: #f8fafc; }

        .event-list { max-height: 150px; overflow-y: auto; font-size: 11px; }
        .event-item { padding: 5px 8px; border-bottom: 1px solid var(--border-color); display: flex; gap: 8px; align-items: flex-start; }
        .event-time { color: var(--text-muted); white-space: nowrap; min-width: 70px; }
        .event-dot { width: 6px; height: 6px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
        .event-dot.critical { background: #dc2626; }
        .event-dot.warning { background: #f59e0b; }
        .event-dot.info { background: #3b82f6; }
        
        .control-group { display: flex; flex-direction: column; gap: 8px; }
        .side-panel::-webkit-scrollbar { width: 4px; }
        .side-panel::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
    </style>
</head>
<body>
    <header>
        <h1>智慧渔业视频分析系统</h1>
        <div id="clock" style="color: var(--text-muted); font-family: monospace; font-size: 14px;"></div>
    </header>

    <div class="alarm-banner" id="alarmBanner">
        <span class="alarm-badge" id="alarmBadge">!</span>
        <span id="alarmText"></span>
    </div>

    <div class="dashboard">
        <div class="video-section">
            <div class="video-header">
                <span>视频监控画面</span>
                <div style="display:flex; align-items:center; gap:10px;">
                    <button class="capture-btn" onclick="captureFrame()" title="保存当前帧">📷 截图</button>
                    <button class="capture-btn" id="recordBtn" onclick="toggleRecording()" title="录制视频">⏺ 录制</button>
                    <span id="statusIndicator" style="color: var(--success); font-weight: 500;">连接正常 | 推理就绪</span>
                </div>
            </div>
            <div class="video-wrapper">
                <video id="videoPlayer" autoplay muted playsinline style="display:none; max-width:100%; max-height:100%; object-fit:contain;"></video>
                <img id="fallbackImg" src="/video_feed" alt="等待视频流接入..." style="max-width:100%; max-height:100%; object-fit:contain;">
            </div>
        </div>

        <div class="resize-handle" id="resizeHandle"></div>

        <div class="side-panel">
            <!-- 传感器卡片 -->
            <div class="card">
                <h3>环境实时指标 (IoT)</h3>
                <div class="sensor-grid">
                    <div class="sensor-item">
                        <div class="sensor-label">水温</div>
                        <div class="sensor-value"><span id="sensor-temp">--</span><span class="sensor-unit">°C</span></div>
                    </div>
                    <div class="sensor-item">
                        <div class="sensor-label">pH值</div>
                        <div class="sensor-value"><span id="sensor-ph">--</span></div>
                    </div>
                    <div class="sensor-item">
                        <div class="sensor-label">溶解氧</div>
                        <div class="sensor-value"><span id="sensor-oxygen">--</span><span class="sensor-unit">mg/L</span></div>
                    </div>
                </div>
                <div id="last-update" style="font-size: 10px; color: var(--text-muted); text-align: right; margin-top: 5px;">最后同步: 未连接</div>
                <div class="chart-wrap"><canvas id="sensorChart"></canvas></div>
            </div>

            <!-- 事件日志卡片 -->
            <div class="card">
                <h3>异常事件日志</h3>
                <div class="event-list" id="eventList">
                    <div style="color:var(--text-muted); text-align:center; padding:10px;">暂无异常事件</div>
                </div>
            </div>

            <!-- AI 视觉控制卡片 -->
            <div class="card">
                <h3>AI 视觉中枢</h3>
                <div class="control-group">
                    <button id="aiBtn" class="btn-on" onclick="toggleAI()">目标检测中</button>
                    <div style="display: flex; gap: 8px;">
                        <button id="enhanceBtn" class="btn-off" onclick="toggleEnhancement()" style="flex: 1;">图像增强</button>
                        <button id="segBtn" class="btn-off" onclick="toggleSegmentation()" style="flex: 1;">实例分割</button>
                    </div>
                    <select id="modelSelect" onchange="switchModel()">
                        <option value="fish_detect_ema">模型：鱼群分析 (标准 EMA)</option>
                        <option value="fish_detect_seam">模型：鱼群分析 (改进 SEAM)</option>
                        <option value="fish_onnx">模型：鱼群分析 (ONNX)</option>
                        <option value="disease_alert">模型：病害告警</option>
                        <option value="fish_seg">模型：鳗鱼分割 (YOLO-seg)</option>
                        <option value="fish_seg_nano">模型：鳗鱼分割 (YOLO-seg Nano)</option>
                        <option value="fish_seg_yolo11">模型：鳗鱼分割 (YOLO11 Nano)</option>
                        <option value="fish_seg_yolo11_onnx">模型：鳗鱼分割 (YOLO11 Nano ONNX)</option>
                        <option value="fish_seg_nano_onnx">模型：鳗鱼分割 (YOLO-seg Nano ONNX)</option>
                        <option value="fish_bifpn">模型：鱼群分析 (ECA+EMA+BiFPN)</option>
                    </select>
                </div>
            </div>

            <!-- AI 智慧对话卡片 (占据剩余空间) -->
            <div class="card" style="border-top: 3px solid #f59e0b; flex: 1; display: flex; flex-direction: column; min-height: 0;">
                <h3>AI 智慧养殖对话</h3>
                <div id="chat-messages" class="chat-messages">
                    <div class="msg msg-ai">你好！我是你的养殖顾问。有什么我可以帮你的吗？你可以直接问我，或者点下面的按钮生成环境报告。</div>
                </div>
                
                <div style="padding: 5px 8px;">
                    <button id="aiAdviceBtn" onclick="getAIAdvice()" style="background: #fffbeb; border-color: #f59e0b; color: #b45309; height: 30px;">
                         生成当前环境实时诊断报告
                    </button>
                </div>

                <div class="chat-input-area">
                    <input type="text" id="chatInput" placeholder="输入问题..." onkeydown="if(event.keyCode==13) sendChatMessage()">
                    <button class="send-btn" onclick="sendChatMessage()">发送</button>
                </div>
            </div>
        </div>
    </div>

    <div class="capture-toast" id="captureToast">✅ 截图已保存</div>

    <script>
        // 全局认证 Token
        var AUTH_TOKEN = 'fishery2026';
        function authFetch(url, opts) {
            opts = opts || {};
            opts.headers = opts.headers || {};
            opts.headers['Authorization'] = 'Bearer ' + AUTH_TOKEN;
            return fetch(url, opts);
        }

        // ------ 侧边栏拖拽调整宽度 ------
        (function() {
            var handle = document.getElementById('resizeHandle');
            var panel  = document.querySelector('.side-panel');
            var saved  = localStorage.getItem('sidePanelWidth');
            if (saved) { panel.style.flexBasis = saved + 'px'; }

            var dragging = false, startX, startW;
            handle.addEventListener('mousedown', function(e) {
                dragging = true; startX = e.clientX;
                startW = panel.getBoundingClientRect().width;
                handle.classList.add('active');
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
                e.preventDefault();
            });
            document.addEventListener('mousemove', function(e) {
                if (!dragging) return;
                var w = startW - (e.clientX - startX);
                w = Math.max(320, Math.min(700, w));
                panel.style.flexBasis = w + 'px';
                panel.style.flexGrow = '0';
                panel.style.flexShrink = '0';
            });
            document.addEventListener('mouseup', function() {
                if (!dragging) return;
                dragging = false;
                handle.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                localStorage.setItem('sidePanelWidth', panel.getBoundingClientRect().width);
            });
        })();

        function updateClock() {
            const now = new Date();
            document.getElementById('clock').innerText = now.toLocaleString();
        }
        setInterval(updateClock, 1000);
        updateClock();

        // 基础控制函数
        function toggleAI() {
            authFetch('/toggle_ai', {method: 'POST'})
            .then(r => r.json()).then(d => {
                let b = document.getElementById('aiBtn');
                b.className = d.ai_enabled ? 'btn-on' : 'btn-off';
                b.innerText = d.ai_enabled ? '目标检测中' : '检测已休眠';
            });
        }
        function toggleEnhancement() {
            authFetch('/toggle_enhancement', {method: 'POST'})
            .then(r => r.json()).then(d => {
                let b = document.getElementById('enhanceBtn');
                b.className = d.enhancement_enabled ? 'btn-on' : 'btn-off';
            });
        }
        function toggleSegmentation() {
            authFetch('/toggle_segmentation', {method: 'POST'})
            .then(r => r.json()).then(d => {
                let b = document.getElementById('segBtn');
                b.className = d.seg_enabled ? 'btn-on' : 'btn-off';
            });
        }
        function switchModel() {
            let m = document.getElementById('modelSelect').value;
            authFetch('/switch_model', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_key: m })
            });
        }

        // 传感器更新
        function updateSensors() {
            authFetch('/get_sensor').then(r => r.json()).then(d => {
                document.getElementById('sensor-temp').innerText = d.temp;
                document.getElementById('sensor-ph').innerText = d.ph;
                document.getElementById('sensor-oxygen').innerText = d.oxygen;
                document.getElementById('last-update').innerText = "最后同步: " + d.last_update;
            }).catch(function(){});
        }

        // 视频录制
        var _recording = false;
        function toggleRecording() {
            var btn = document.getElementById('recordBtn');
            var endpoint = _recording ? '/stop_recording' : '/start_recording';
            btn.disabled = true;
            authFetch(endpoint, { method: 'POST' })
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    if (d.status === 'success') {
                        _recording = !_recording;
                        btn.innerText = _recording ? '⏹ 停止' : '⏺ 录制';
                        btn.style.color = _recording ? '#dc2626' : '';
                        btn.style.borderColor = _recording ? '#dc2626' : '';
                    }
                    if (d.filename) {
                        var toast = document.getElementById('captureToast');
                        toast.innerText = '⏺ 开始录制: ' + d.filename;
                        toast.classList.add('show');
                        setTimeout(function() { toast.classList.remove('show'); }, 2000);
                    }
                })
                .catch(function() {})
                .finally(function() { btn.disabled = false; });
        }

        // 截图保存
        function captureFrame() {
            const btn = document.querySelector('.capture-btn');
            btn.disabled = true;
            btn.innerText = '⏳ ...';
            authFetch('/capture_frame', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    const toast = document.getElementById('captureToast');
                    if (d.status === 'success') {
                        toast.innerText = '✅ 已保存: ' + d.filename;
                    } else {
                        toast.innerText = '❌ 截图失败: ' + d.message;
                    }
                    toast.classList.add('show');
                    setTimeout(function() { toast.classList.remove('show'); }, 2000);
                })
                .catch(function() {
                    const toast = document.getElementById('captureToast');
                    toast.innerText = '❌ 截图请求失败';
                    toast.classList.add('show');
                    setTimeout(function() { toast.classList.remove('show'); }, 2000);
                })
                .finally(function() {
                    btn.disabled = false;
                    btn.innerText = '📷 截图';
                });
        }

        setInterval(updateSensors, 5000);
        updateSensors();

        // ------ 连接健康检查 ------
        var _healthFailures = 0;
        function checkHealth() {
            authFetch('/health')
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    var status = document.getElementById('statusIndicator');
                    _healthFailures = 0;
                    if (!d.stream_ok) {
                        status.innerText = '视频流断连 | 重连中...';
                        status.style.color = '#dc2626';
                    } else if (d.recording) {
                        status.innerText = '录制中 | 推理就绪';
                        status.style.color = '#dc2626';
                    } else {
                        status.innerText = '连接正常 | 推理就绪';
                        status.style.color = '#16a34a';
                    }
                })
                .catch(function() {
                    _healthFailures++;
                    var status = document.getElementById('statusIndicator');
                    status.innerText = '服务器无响应 | 检查网络';
                    status.style.color = '#dc2626';
                });
        }
        setInterval(checkHealth, 5000);
        checkHealth();

        // MJPEG 图片加载错误检测
        var fallbackImg = document.getElementById('fallbackImg');
        fallbackImg.addEventListener('error', function() {
            var status = document.getElementById('statusIndicator');
            status.innerText = '视频流断开 | 等待恢复...';
            status.style.color = '#dc2626';
            // 每 3 秒重试加载
            var retryTimer = setInterval(function() {
                var src = fallbackImg.src;
                fallbackImg.src = '';
                fallbackImg.src = src;
                if (fallbackImg.naturalWidth > 0) {
                    clearInterval(retryTimer);
                    checkHealth();
                }
            }, 3000);
        });
        fallbackImg.addEventListener('load', function() {
            if (document.getElementById('statusIndicator').innerText.indexOf('断开') >= 0) {
                checkHealth();
            }
        });

        // ------ 告警检测 ------
        function checkAlarm() {
            authFetch('/check_alarm')
                .then(r => r.json())
                .then(d => {
                    var banner = document.getElementById('alarmBanner');
                    var badge = document.getElementById('alarmBadge');
                    var text  = document.getElementById('alarmText');
                    if (!d.alarms || d.alarms.length === 0) {
                        banner.className = 'alarm-banner';
                        return;
                    }
                    var worst = d.alarms[0];
                    for (var i = 1; i < d.alarms.length; i++) {
                        if (d.alarms[i].level === 'critical') { worst = d.alarms[i]; break; }
                    }
                    banner.className = 'alarm-banner ' + worst.level;
                    badge.className = 'alarm-badge ' + worst.level;
                    badge.innerText = worst.level === 'critical' ? '危急' : '警告';
                    text.innerText = worst.message;
                    if (worst.level === 'critical') {
                        text.innerText += '（共 ' + d.alarms.length + ' 项异常）';
                    }
                }).catch(function(){});
        }
        setInterval(checkAlarm, 3000);
        checkAlarm();

        // ------ 传感器历史曲线 ------
        (function() {
            var canvas = document.getElementById('sensorChart');
            var ctx = canvas.getContext('2d');
            var history = [];  // [{time, temp, ph, oxygen}]
            var MAX_POINTS = 60; // 2 小时 (每 2 分钟一条 = 120 分钟)

            function drawChart() {
                var W = canvas.parentElement.clientWidth;
                var H = 80;
                canvas.width = W * (window.devicePixelRatio || 1);
                canvas.height = H * (window.devicePixelRatio || 1);
                canvas.style.width = W + 'px';
                canvas.style.height = H + 'px';
                ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
                ctx.clearRect(0, 0, W, H);

                if (history.length < 2) {
                    ctx.fillStyle = '#94a3b8';
                    ctx.font = '11px monospace';
                    ctx.fillText('等待数据...', 10, H/2 + 4);
                    return;
                }

                var colors = { temp: '#ef4444', ph: '#8b5cf6', oxygen: '#06b6d4' };
                var labels = { temp: '水温°C', ph: 'pH', oxygen: '溶氧mg/L' };
                var keys = ['temp', 'ph', 'oxygen'];

                // 找每项的范围
                for (var ki = 0; ki < keys.length; ki++) {
                    var k = keys[ki];
                    var vals = history.map(function(p) { return parseFloat(p[k]) || 0; });
                    var min = Math.min.apply(null, vals);
                    var max = Math.max.apply(null, vals);
                    var range = max - min || 1;
                    var pad = range * 0.2;
                    min -= pad; max += pad;
                    var stepX = W / (history.length - 1);

                    ctx.beginPath();
                    ctx.strokeStyle = colors[k];
                    ctx.lineWidth = 1.5;
                    for (var i = 0; i < vals.length; i++) {
                        var x = i * stepX;
                        var y = H - 8 - ((vals[i] - min) / (max - min)) * (H - 20);
                        if (i === 0) ctx.moveTo(x, y);
                        else ctx.lineTo(x, y);
                    }
                    ctx.stroke();

                    // 标签
                    ctx.fillStyle = colors[k];
                    ctx.font = '9px monospace';
                    var lastVal = vals[vals.length - 1];
                    ctx.fillText(labels[k] + ' ' + lastVal.toFixed(1), W - 120 + ki*45, ki*14 + 12);
                }

                // X 轴时间标记
                ctx.fillStyle = '#94a3b8';
                ctx.font = '9px monospace';
                var first = history[0].time;
                var last = history[history.length-1].time;
                ctx.fillText(first, 2, H - 2);
                ctx.fillText(last, W - 40, H - 2);
            }

            // 每 2 分钟记录一次数据点（不影响传感器的 2s 刷新）
            function recordPoint() {
                var temp = document.getElementById('sensor-temp').innerText;
                var ph   = document.getElementById('sensor-ph').innerText;
                var oxy  = document.getElementById('sensor-oxygen').innerText;
                if (temp === '--') return;
                var now = new Date();
                history.push({
                    time: now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0'),
                    temp: temp, ph: ph, oxygen: oxy
                });
                while (history.length > MAX_POINTS) history.shift();
                drawChart();
            }
            // 从服务器加载历史数据
            authFetch('/get_sensor_history')
                .then(function(r) { return r.json(); })
                .then(function(rows) {
                    if (rows.length > 0) {
                        history = rows.map(function(r) {
                            var d = new Date(r.time * 1000);
                            return {
                                time: d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0'),
                                temp: r.temp, ph: r.ph, oxygen: r.oxygen
                            };
                        });
                        drawChart();
                    }
                }).catch(function(){});
            setInterval(recordPoint, 120000); // 每 2 分钟
            setTimeout(recordPoint, 5000);     // 启动后 5 秒先采一次
            window.addEventListener('resize', drawChart);
        })();

        // ------ 事件日志更新 ------
        function updateEventLog() {
            authFetch('/get_events')
                .then(r => r.json())
                .then(d => {
                    var list = document.getElementById('eventList');
                    if (!d.events || d.events.length === 0) {
                        list.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:10px;">暂无异常事件</div>';
                        return;
                    }
                    var html = '';
                    d.events.forEach(function(e) {
                        html += '<div class="event-item">' +
                            '<span class="event-time">' + e.time + '</span>' +
                            '<span class="event-dot ' + e.level + '"></span>' +
                            '<span>' + e.message + '</span></div>';
                    });
                    list.innerHTML = html;
                }).catch(function(){});
        }
        setInterval(updateEventLog, 5000);
        updateEventLog();

        // --- AI 对话逻辑 ---
        const messagesContainer = document.getElementById('chat-messages');

        function sanitizeHTML(str) {
            return str.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
                      .replace(/\bon\w+\s*=\s*"[^"]*"/gi, '')
                      .replace(/\bon\w+\s*=\s*'[^']*'/gi, '')
                      .replace(/javascript\s*:/gi, 'blocked:');
        }

        function addMessage(text, role) {
            const div = document.createElement('div');
            div.className = `msg msg-${role}`;
            if (role === 'ai') {
                div.innerHTML = sanitizeHTML(marked.parse(text));
            } else {
                div.innerText = text;
            }
            messagesContainer.appendChild(div);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function sendChatMessage() {
            const input = document.getElementById('chatInput');
            const text = input.value.trim();
            if (!text) return;

            addMessage(text, 'user');
            input.value = '';

            // 显示加载状态
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'msg msg-ai';
            loadingDiv.innerText = '正在思考...';
            messagesContainer.appendChild(loadingDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            authFetch('/chat_ai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            })
            .then(r => r.json())
            .then(data => {
                messagesContainer.removeChild(loadingDiv);
                addMessage(data.response, 'ai');
            })
            .catch(() => {
                messagesContainer.removeChild(loadingDiv);
                addMessage('⚠️ 对话请求失败，请检查网络。', 'ai');
            });
        }

        function getAIAdvice() {
            addMessage('✨ 正在生成当前环境的实时诊断报告...', 'user');
            
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'msg msg-ai';
            loadingDiv.innerText = '正在分析传感器数据，请稍候...';
            messagesContainer.appendChild(loadingDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            authFetch('/get_ai_advice', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                messagesContainer.removeChild(loadingDiv);
                addMessage(data.advice, 'ai');
            })
            .catch(() => {
                messagesContainer.removeChild(loadingDiv);
                addMessage('⚠️ 诊断请求失败。', 'ai');
            });
        }

    (function() {
        // 检测浏览器支持的 AVC1 codec
        const MIME_CODECS = [
            'video/mp4; codecs="avc1.42E01F"',   // Baseline 3.1 (当前编码器输出)
            'video/mp4; codecs="avc1.42E028"',   // Baseline 4.0
            'video/mp4; codecs="avc1.42C01E"',   // Baseline 3.1 (alt)
            'video/mp4; codecs="avc1.42E01E"',   // Baseline 3.0
            'video/mp4; codecs="avc1.42001E"',   // Baseline 3.0 (alt)
        ];
        let MIME_CODEC = MIME_CODECS[0];
        if (window.MediaSource && window.MediaSource.isTypeSupported) {
            const found = MIME_CODECS.find(c => window.MediaSource.isTypeSupported(c));
            if (found) MIME_CODEC = found;
        }

        const video   = document.getElementById('videoPlayer');
        const fallback = document.getElementById('fallbackImg');

        let ws = null;
        let ms = null;
        let sb = null;
        let sbReady = false;
        let pending = [];         // 待追加的 media segment 队列
        let initBuffer = null;    // 缓存 init segment，等 sb 就绪再追加
        let reconnectTimer = null;
        let connected = false;
        let h264Active = false;   // 当前是否正在播放 H.264

        /* ========== 显示切换（不改动 MJPEG src） ========== */

        /** 切回 MJPEG（已在后台持续播放，仅切换显示元素） */
        function showMJPEG() {
            if (!h264Active) return; // 已经是 MJPEG，无需操作
            h264Active = false;
            video.style.display = 'none';
            fallback.style.display = 'block';
            cleanupMS();
        }

        /** 切换到 H.264 视频 */
        function showH264() {
            h264Active = true;
            fallback.style.display = 'none';
            video.style.display = 'block';
            video.play().catch(function() {});
        }

        /* ========== MediaSource 生命周期 ========== */

        function cleanupMS() {
            sbReady = false;
            sb = null;
            pending = [];
            initBuffer = null;
            if (ms && ms.readyState === 'open') {
                try { ms.endOfStream(); } catch(_) {}
            }
            if (video.src) {
                URL.revokeObjectURL(video.src);
                video.src = '';
            }
            ms = null;
        }

        /** 创建 MediaSource + SourceBuffer（不切换显示） */
        function setupMediaSource() {
            cleanupMS();

            if (!window.MediaSource || !MediaSource.isTypeSupported(MIME_CODEC)) {
                console.log('[MSE] H.264 不被浏览器支持，保持 MJPEG');
                return false;
            }

            ms = new MediaSource();
            video.src = URL.createObjectURL(ms);

            ms.onsourceopen = function() {
                try {
                    sb = ms.addSourceBuffer(MIME_CODEC);
                    sb.onupdateend = function() {
                        if (pending.length > 0) {
                            var seg = pending.shift();
                            try { sb.appendBuffer(seg); } catch(_) {}
                        }
                    };
                    sb.onerror = function() {
                        console.error('[MSE] SourceBuffer 错误');
                    };
                    sbReady = true;
                    // 如果 init segment 先于 onsourceopen 到达，补追加
                    if (initBuffer) {
                        sb.appendBuffer(initBuffer);
                        initBuffer = null;
                    }
                } catch(e) {
                    console.error('[MSE] addSourceBuffer 失败:', e);
                    showMJPEG();
                }
            };

            return true;
        }

        /* ========== WebSocket 连接 ========== */

        function connectWS() {
            if (ws) { try { ws.close(); } catch(_) {} }
            if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }

            var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + location.host + '/ws_video');
            ws.binaryType = 'arraybuffer';

            var initSent = false; // 每次新连接重置

            ws.onopen = function() {
                connected = true;
                var status = document.getElementById('statusIndicator');
                status.innerText = 'H.264 已连接 | 推理就绪';
                status.style.color = '#16a34a';
            };

            ws.onmessage = function(e) {
                // --- 文本消息（meta / error） ---
                if (typeof e.data === 'string') {
                    try {
                        var msg = JSON.parse(e.data);
                        if (msg.type === 'meta') {
                            video.width  = msg.width;
                            video.height = msg.height;
                        } else if (msg.type === 'error') {
                            console.error('[WS]', msg.message);
                            showMJPEG();
                        }
                    } catch(_) {}
                    return;
                }

                // --- 二进制数据 ---
                if (!h264Active) {
                    // 首个二进制消息 → 初始化 MSE 并切换到 H.264 显示
                    if (!setupMediaSource()) {
                        return; // MSE 不支持，保持 MJPEG
                    }
                    showH264();
                }

                if (!initSent) {
                    // 第一个二进制 = init segment (ftyp+moov)
                    initSent = true;
                    if (sbReady && sb && !sb.updating) {
                        sb.appendBuffer(e.data);
                    } else {
                        initBuffer = e.data;
                    }
                    return;
                }

                // media segment
                if (sbReady && sb && !sb.updating) {
                    sb.appendBuffer(e.data);
                } else {
                    pending.push(e.data);
                }
            };

            ws.onclose = function() {
                connected = false;
                showMJPEG();
                var status = document.getElementById('statusIndicator');
                status.innerText = 'H.264 断开 | 使用 MJPEG 回退';
                status.style.color = '#f59e0b';
                // 页面可见时自动重连
                if (!document.hidden) {
                    reconnectTimer = setTimeout(function() { connectWS(); }, 3000);
                }
            };

            ws.onerror = function() { ws.close(); };
        }

        /* ========== 标签页可见性 ========== */

        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
                if (ws) { ws.close(); }
            } else {
                if (!connected) { connectWS(); }
            }
        });

        /* ========== 启动 ========== */

        // MJPEG 已通过 <img src="/video_feed"> 在后台播放
        // 仅启动 WebSocket 后台连接，收到 H.264 数据后自动切换
        connectWS();
    })();
    </script>
</body>
</html>