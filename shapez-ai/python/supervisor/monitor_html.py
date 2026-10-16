"""
AI Reasoning Monitor Web Dashboard (N-0.3.0).
Interactive Dark Violet real-time cockpit with two-way chat, persistent history search,
native <think> reasoning stream, mods understanding, and factory engineering diagnostics.
Author: QXIK_mIJ
License: Apache License 2.0
"""

MONITOR_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shapez AI — Cognitive Engineering Cockpit N-0.3.0</title>
    <style>
        :root {
            --bg-base: #0a0512;
            --bg-panel: #140a24;
            --bg-card: #1c0e33;
            --bg-hover: #261345;
            --border-glow: rgba(157, 78, 221, 0.4);
            --border-bright: #9d4edd;
            --text-main: #f1e4ff;
            --text-dim: #b892ff;
            --text-muted: #8263a8;
            --accent-cyan: #00f5d4;
            --accent-green: #38b000;
            --accent-amber: #ffb703;
            --accent-red: #ff0054;
            --accent-purple: #c77dff;
            --font-mono: "Fira Code", Consolas, "Courier New", monospace;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            padding: 16px 24px;
            min-height: 100vh;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 14px;
            border-bottom: 1px solid var(--border-glow);
            margin-bottom: 18px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header-title h1 {
            font-size: 19px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: linear-gradient(90deg, #c77dff, #00f5d4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .badge {
            background: rgba(157, 78, 221, 0.2);
            border: 1px solid var(--border-bright);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            color: var(--accent-cyan);
            font-family: var(--font-mono);
        }
        .header-controls {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .session-select {
            background: var(--bg-card);
            border: 1px solid var(--border-bright);
            color: var(--accent-cyan);
            padding: 6px 12px;
            border-radius: 6px;
            font-family: var(--font-mono);
            font-size: 12px;
            cursor: pointer;
            outline: none;
        }
        .btn {
            background: rgba(157, 78, 221, 0.2);
            border: 1px solid var(--border-bright);
            color: var(--text-main);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            outline: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn:hover {
            background: rgba(157, 78, 221, 0.45);
            border-color: var(--accent-purple);
            transform: translateY(-1px);
        }
        .btn-pause {
            background: rgba(255, 183, 3, 0.2);
            border-color: var(--accent-amber);
            color: var(--accent-amber);
        }
        .btn-pause:hover {
            background: rgba(255, 183, 3, 0.4);
        }
        .btn-pause.active {
            background: rgba(56, 176, 0, 0.25);
            border-color: var(--accent-green);
            color: var(--accent-green);
        }
        .btn-pause.active:hover {
            background: rgba(56, 176, 0, 0.45);
        }
        .status-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
            transition: all 0.3s ease;
        }
        .status-dot.paused {
            background: var(--accent-amber);
            box-shadow: 0 0 8px var(--accent-amber);
        }
        .status-dot.error {
            background: var(--accent-red);
            box-shadow: 0 0 8px var(--accent-red);
        }
        .grid-top {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 18px;
        }
        .metric-card {
            background: var(--bg-panel);
            border: 1px solid var(--border-glow);
            border-radius: 8px;
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
        }
        .metric-title {
            font-size: 11px;
            text-transform: uppercase;
            color: var(--text-dim);
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 20px;
            font-weight: 700;
            color: var(--accent-cyan);
            font-family: var(--font-mono);
        }
        .metric-sub {
            font-size: 11px;
            color: var(--text-muted);
        }
        .grid-main {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin-bottom: 18px;
        }
        .card {
            background: var(--bg-panel);
            border: 1px solid var(--border-glow);
            border-radius: 8px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-height: 220px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(157, 78, 221, 0.25);
            padding-bottom: 8px;
        }
        .card-header h2 {
            font-size: 13px;
            font-weight: 600;
            color: var(--accent-purple);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .content-box {
            font-size: 12px;
            line-height: 1.5;
            color: var(--text-main);
            flex-grow: 1;
            overflow-y: auto;
            max-height: 220px;
        }
        .thought-box {
            background: var(--bg-card);
            border-left: 3px solid var(--accent-purple);
            padding: 10px;
            border-radius: 4px;
            font-size: 12px;
            color: #ebd7ff;
            line-height: 1.45;
        }
        .cot-box {
            background: #06020a;
            border: 1px solid rgba(157, 78, 221, 0.3);
            border-radius: 4px;
            padding: 10px;
            font-family: var(--font-mono);
            font-size: 11px;
            color: #d1b3ff;
            white-space: pre-wrap;
            max-height: 180px;
            overflow-y: auto;
            line-height: 1.4;
        }
        .actions-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .action-item {
            background: var(--bg-card);
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 11px;
            font-family: var(--font-mono);
            display: flex;
            justify-content: space-between;
            border-left: 3px solid var(--accent-cyan);
        }
        .action-item.failed {
            border-left-color: var(--accent-red);
        }
        .mods-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .mod-tag {
            background: rgba(157, 78, 221, 0.15);
            border: 1px solid rgba(157, 78, 221, 0.4);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            color: var(--text-dim);
        }
        /* Bottom interactive cockpit tabs */
        .bottom-section {
            background: var(--bg-panel);
            border: 1px solid var(--border-glow);
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .tabs-header {
            display: flex;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-glow);
        }
        .tab-btn {
            background: none;
            border: none;
            color: var(--text-dim);
            padding: 10px 18px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .tab-btn:hover {
            color: var(--text-main);
            background: rgba(157, 78, 221, 0.1);
        }
        .tab-btn.active {
            color: var(--accent-cyan);
            border-bottom-color: var(--accent-cyan);
            background: rgba(157, 78, 221, 0.15);
        }
        .tab-content {
            display: none;
            padding: 16px;
        }
        .tab-content.active {
            display: block;
        }
        /* Chat styles */
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 400px;
        }
        .chat-messages {
            display: flex;
            flex-direction: column;
            gap: 10px;
            height: 240px;
            overflow-y: auto;
            padding-right: 8px;
        }
        .chat-msg {
            display: flex;
            flex-direction: column;
            max-width: 80%;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            line-height: 1.45;
        }
        .chat-msg.player {
            align-self: flex-end;
            background: rgba(157, 78, 221, 0.3);
            border: 1px solid var(--border-bright);
            color: #ffffff;
        }
        .chat-msg.ai {
            align-self: flex-start;
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            color: #e2ccff;
        }
        .chat-msg-time {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 4px;
            align-self: flex-end;
        }
        .chat-suggestions {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .suggestion-pill {
            background: rgba(157, 78, 221, 0.15);
            border: 1px solid rgba(157, 78, 221, 0.35);
            color: var(--text-dim);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .suggestion-pill:hover {
            background: rgba(157, 78, 221, 0.35);
            color: var(--accent-cyan);
            border-color: var(--accent-cyan);
        }
        .chat-input-row {
            display: flex;
            gap: 10px;
        }
        .chat-input {
            flex-grow: 1;
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 6px;
            padding: 8px 12px;
            color: var(--text-main);
            font-size: 12px;
            outline: none;
        }
        .chat-input:focus {
            border-color: var(--accent-purple);
        }
        /* History styles */
        .history-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        .history-search {
            flex-grow: 1;
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 6px;
            padding: 6px 12px;
            color: var(--text-main);
            font-size: 12px;
            outline: none;
        }
        .history-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-height: 320px;
            overflow-y: auto;
        }
        .history-entry {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 6px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .history-header {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            font-family: var(--font-mono);
            color: var(--text-dim);
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>SHAPEZ AI COGNITIVE MONITOR</h1>
            <span class="badge">vN-0.3.0</span>
            <div class="status-pill">
                <div class="status-dot paused" id="status-dot"></div>
                <span id="status-text">PAUSED</span>
            </div>
        </div>
        <div class="header-controls">
            <button class="btn btn-pause" id="btn-pause-toggle" onclick="togglePause()">▶ Возобновить ИИ</button>
            <select class="session-select" id="session-select" onchange="changeSession()">
                <option value="session_primary">session_primary</option>
            </select>
            <button class="btn" onclick="triggerReplan()">🔄 Перепланировать</button>
            <button class="btn" onclick="moveWindow(1)">🖥 Монитор 1</button>
            <button class="btn" onclick="moveWindow(2)">🖥 Монитор 2</button>
        </div>
    </header>

    <div class="grid-top">
        <div class="metric-card">
            <span class="metric-title">Текущая цель & Уровень</span>
            <span class="metric-value" id="val-level">Lvl 1: CuCuCuCu</span>
            <span class="metric-sub" id="val-progress">0 / 30 доставлено</span>
        </div>
        <div class="metric-card">
            <span class="metric-title">Темп поставки (Throughput)</span>
            <span class="metric-value" id="val-throughput">0.0 /s</span>
            <span class="metric-sub" id="val-fps">60 FPS</span>
        </div>
        <div class="metric-card">
            <span class="metric-title">Задержки LLM & Сборки</span>
            <span class="metric-value" id="val-latencies">0ms / 0ms</span>
            <span class="metric-sub" id="val-model">Модель: Qwen3.5-9B-Q8_0</span>
        </div>
        <div class="metric-card">
            <span class="metric-title">Состояние мира & Ревизия</span>
            <span class="metric-value" id="val-revision">Rev #1</span>
            <span class="metric-sub" id="val-status-detail">Watchdog активен</span>
        </div>
    </div>

    <div class="grid-main">
        <!-- 1. Текущая цель и план развития -->
        <div class="card">
            <div class="card-header">
                <h2>🎯 Задача и Дорожная карта</h2>
                <span class="badge" id="badge-goal-type">Direct Route</span>
            </div>
            <div class="content-box">
                <div style="margin-bottom: 8px;">
                    <strong>Текущий этап:</strong> <span id="txt-active-phase">Ожидание запуска</span>
                </div>
                <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 6px;">
                    <strong>Краткосрочный план:</strong>
                </div>
                <ul id="list-short-plan" style="padding-left: 18px; margin-bottom: 10px; font-size: 11px;">
                    <li>Определение ресурсной залежи</li>
                    <li>Построение конвейера с turn-penalty</li>
                    <li>Проверка preflight check и запуск линии</li>
                </ul>
                <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 6px;">
                    <strong>Долгосрочная стратегия:</strong>
                </div>
                <ul id="list-long-plan" style="padding-left: 18px; font-size: 11px; color: var(--text-muted);">
                    <li>Базовая добыча (Lvl 1-3)</li>
                    <li>Модульная резка (Lvl 4-7)</li>
                    <li>Смешивание и окраска (Lvl 8-11)</li>
                </ul>
            </div>
        </div>

        <!-- 2. Архитектурное объяснение -->
        <div class="card">
            <div class="card-header">
                <h2>🧠 Архитектурное решение (AI Strategy)</h2>
                <span class="badge" id="badge-patch">Patch (0, 0)</span>
            </div>
            <div class="content-box">
                <div class="thought-box" id="txt-thought">
                    Нажмите «Возобновить ИИ» или введите указание в чате, чтобы начать автономное планирование.
                </div>
                <div style="margin-top: 10px; font-size: 11px; color: var(--text-dim);">
                    <strong>Инженерные предпочтения:</strong>
                    <div style="display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap;">
                        <span class="badge">Компактность</span>
                        <span class="badge">Симметрия</span>
                        <span class="badge">Манхэттен-шины</span>
                        <span class="badge">Повторное использование</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 3. Настоящий поток мыслей LLM (Chain of Thought / <think>) -->
        <div class="card">
            <div class="card-header">
                <h2>⚡ Native CoT (<think> Stream)</h2>
                <span class="badge" id="badge-cot-len">0 tokens</span>
            </div>
            <div class="content-box">
                <div class="cot-box" id="txt-cot">Поток внутренних рассуждений модели появится после генерации решения...</div>
            </div>
        </div>

        <!-- 4. Инженерный чертеж и топология -->
        <div class="card">
            <div class="card-header">
                <h2>📐 Топология фабрики</h2>
                <span class="badge" id="badge-components">0 объектов</span>
            </div>
            <div class="content-box">
                <div style="margin-bottom: 8px;">
                    <strong>План сборки:</strong> <span id="txt-plan-action">None</span>
                </div>
                <ul class="actions-list" id="list-actions">
                    <li class="action-item"><span>Ожидание первого плана...</span><span>--</span></li>
                </ul>
            </div>
        </div>

        <!-- 5. Диагностика исполнения & Watchdog -->
        <div class="card">
            <div class="card-header">
                <h2>🛡 Диагностика & Самоисцеление</h2>
                <span class="badge" id="badge-watchdog">Ready</span>
            </div>
            <div class="content-box">
                <div style="margin-bottom: 6px;">
                    <strong>Preflight Check:</strong> <span id="txt-preflight" style="color: var(--accent-green);">Valid</span>
                </div>
                <div style="margin-bottom: 6px;">
                    <strong>Статус Watchdog:</strong> <span id="txt-watchdog-lines">0 активных линий отслеживается</span>
                </div>
                <div style="margin-bottom: 6px;">
                    <strong>Узкие места (Bottlenecks):</strong> <span id="txt-bottlenecks" style="color: var(--accent-cyan);">Не обнаружено</span>
                </div>
                <div id="txt-last-repair" style="font-size: 11px; color: var(--text-muted); margin-top: 8px;">
                    Событий разрушения не зафиксировано.
                </div>
            </div>
        </div>

        <!-- 6. Моды и улучшения Hub -->
        <div class="card">
            <div class="card-header">
                <h2>🧩 Моды & Апгрейды</h2>
                <span class="badge" id="badge-mods-count">14 модов</span>
            </div>
            <div class="content-box">
                <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 4px;"><strong>Активные моды:</strong></div>
                <div class="mods-tags" id="container-mods">
                    <span class="mod-tag">4 way Balancer</span>
                    <span class="mod-tag">Mirrored Buildings</span>
                    <span class="mod-tag">Packaging</span>
                    <span class="mod-tag">Micro Filters</span>
                    <span class="mod-tag">Custom Storage</span>
                    <span class="mod-tag">Edge Rotation</span>
                </div>
                <div style="margin-top: 10px; font-size: 11px; color: var(--text-dim); margin-bottom: 4px;">
                    <strong>Технологические апгрейды:</strong>
                </div>
                <div id="container-upgrades" style="font-size: 11px;">
                    Скорость конвейера: Tier 1 | Добыча: Tier 1 | Обработка: Tier 1
                </div>
            </div>
        </div>
    </div>

    <!-- Bottom Cockpit Section: Interactive Chat and Full Persistent History -->
    <div class="bottom-section">
        <div class="tabs-header">
            <button class="tab-btn active" id="tab-btn-chat" onclick="switchTab('chat')">💬 Интерактивный диалог с ИИ</button>
            <button class="tab-btn" id="tab-btn-history" onclick="switchTab('history')">📜 Полная история решений (Persistent History)</button>
        </div>

        <!-- Tab 1: Interactive Chat -->
        <div class="tab-content active" id="tab-content-chat">
            <div class="chat-container">
                <div class="chat-messages" id="chat-messages">
                    <div class="chat-msg ai">
                        <strong>Shapez AI:</strong> Приветствую, Создатель! Я готов строить фабрику. Вы можете передавать мне любые указания по компактности, симметрии, оптимизации маршрутов или подготовке будущих уровней.
                        <span class="chat-msg-time">Начало сессии</span>
                    </div>
                </div>

                <div class="chat-suggestions">
                    <span class="suggestion-pill" onclick="sendQuickChat('Сделай этот завод максимально компактным')">«Сделай этот завод компактнее»</span>
                    <span class="suggestion-pill" onclick="sendQuickChat('Строй строго симметрично')">«Строй симметрично»</span>
                    <span class="suggestion-pill" onclick="sendQuickChat('Почему ты выбрал такой маршрут?')">«Почему ты выбрал такой маршрут?»</span>
                    <span class="suggestion-pill" onclick="sendQuickChat('Оптимизируй узкие места и линии конвейеров')">«Оптимизируй узкие места»</span>
                    <span class="suggestion-pill" onclick="sendQuickChat('Подготовь инфраструктуру для следующего уровня')">«Подготовь инфраструктуру»</span>
                </div>

                <div class="chat-input-row">
                    <input type="text" class="chat-input" id="chat-input" placeholder="Введите указание для Shapez AI (например: 'Сделай фабрику компактнее')..." onkeydown="if(event.key==='Enter') sendChatMessage()">
                    <button class="btn" style="background: var(--accent-purple); color: #0a0512; font-weight: 700;" onclick="sendChatMessage()">Отправить ↵</button>
                </div>
            </div>
        </div>

        <!-- Tab 2: Full Persistent History -->
        <div class="tab-content" id="tab-content-history">
            <div class="history-controls">
                <input type="text" class="history-search" id="history-search" placeholder="Поиск по истории (цель, решение, ключевое слово)..." oninput="loadHistory()">
                <select class="session-select" id="history-level-filter" onchange="loadHistory()">
                    <option value="0">Все уровни</option>
                    <option value="1">Уровень 1</option>
                    <option value="2">Уровень 2</option>
                    <option value="3">Уровень 3</option>
                    <option value="4">Уровень 4</option>
                </select>
                <select class="session-select" id="history-status-filter" onchange="loadHistory()">
                    <option value="all">Все статусы</option>
                    <option value="success">Успешные</option>
                    <option value="failed">Сбои / Откаты</option>
                </select>
            </div>
            <div class="history-list" id="history-list">
                <div style="color: var(--text-muted); font-size: 12px; text-align: center; padding: 20px;">
                    Загрузка сохраненной истории решений...
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentSessionId = "session_primary";
        let isPaused = true;

        async function fetchState() {
            try {
                const res = await fetch(`/api/session?session_id=${currentSessionId}`);
                if (!res.ok) return;
                const data = await res.json();
                renderState(data);
            } catch (e) {
                console.error("Fetch state error:", e);
            }
        }

        function renderState(s) {
            isPaused = !!s.is_paused;
            const dot = document.getElementById("status-dot");
            const stText = document.getElementById("status-text");
            const btnPause = document.getElementById("btn-pause-toggle");

            if (isPaused) {
                dot.className = "status-dot paused";
                stText.textContent = "PAUSED";
                btnPause.className = "btn btn-pause active";
                btnPause.textContent = "▶ Возобновить ИИ";
            } else {
                dot.className = "status-dot";
                stText.textContent = "ACTIVE";
                btnPause.className = "btn btn-pause";
                btnPause.textContent = "⏸ Пауза ИИ";
            }

            const goal = s.goal || {};
            const shape = goal.shape || "CuCuCuCu";
            const lvl = s.level || 1;
            document.getElementById("val-level").textContent = `Lvl ${lvl}: ${shape}`;
            const req = goal.required || 30;
            const del = goal.delivered || 0;
            document.getElementById("val-progress").textContent = `${del} / ${req} доставлено`;

            const thr = s.throughput || 0;
            document.getElementById("val-throughput").textContent = `${thr.toFixed(1)} /s`;
            document.getElementById("val-fps").textContent = `${Math.round(s.fps || 60)} FPS`;
            document.getElementById("val-revision").textContent = `Rev #${s.world_revision || 1}`;

            const phase = s.state_machine_stage || (isPaused ? "PAUSED" : "OPERATING");
            const phaseElem = document.getElementById("txt-active-phase");
            if (phaseElem) phaseElem.textContent = phase;

            // Check latest reasoning entry
            if (s.history && s.history.length > 0) {
                const latest = s.history[s.history.length - 1];
                document.getElementById("val-latencies").textContent = `${Math.round(latest.llm_latency_ms)}ms / ${Math.round(latest.execution_latency_ms)}ms`;
                document.getElementById("txt-thought").textContent = latest.thought || "--";
                document.getElementById("txt-plan-action").textContent = latest.plan_action || "--";

                if (latest.reasoning_content) {
                    document.getElementById("txt-cot").textContent = latest.reasoning_content;
                    document.getElementById("badge-cot-len").textContent = `${latest.reasoning_content.length} chars`;
                } else {
                    document.getElementById("txt-cot").textContent = "Native reasoning поток пуст (модель выдала прямой ответ).";
                    document.getElementById("badge-cot-len").textContent = "0 chars";
                }

                if (latest.chosen_patch && latest.chosen_patch.tileX !== undefined) {
                    document.getElementById("badge-patch").textContent = `Patch (${Math.round(latest.chosen_patch.tileX)}, ${Math.round(latest.chosen_patch.tileY)})`;
                }

                // Dispatched actions
                const acts = latest.dispatched_actions || [];
                const actList = document.getElementById("list-actions");
                if (acts.length > 0) {
                    actList.innerHTML = acts.map(a => `
                        <li class="action-item ${a.error ? 'failed' : ''}">
                            <span>${a.command} (${JSON.stringify(a.params)})</span>
                            <span>${a.duration_ms ? Math.round(a.duration_ms) + 'ms' : (a.error ? 'ERR' : 'OK')}</span>
                        </li>
                    `).join("");
                }
            }

            // Chat render
            if (s.chat_history && s.chat_history.length > 0) {
                const chatBox = document.getElementById("chat-messages");
                chatBox.innerHTML = s.chat_history.map(m => `
                    <div class="chat-msg ${m.sender}">
                        <strong>${m.sender === 'player' ? 'Создатель (Вы)' : 'Shapez AI'}:</strong> ${escapeHtml(m.text)}
                        <span class="chat-msg-time">${new Date(m.timestamp * 1000).toLocaleTimeString()}</span>
                    </div>
                `).join("");
            }
        }

        async function togglePause() {
            const nextPaused = !isPaused;
            try {
                await fetch("/api/pause", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ session_id: currentSessionId, paused: nextPaused })
                });
                await fetchState();
            } catch (e) {
                console.error("Toggle pause failed:", e);
            }
        }

        async function triggerReplan() {
            try {
                await fetch(`/api/plan?session_id=${currentSessionId}`, { method: "POST" });
                await fetchState();
            } catch (e) {
                console.error("Replan failed:", e);
            }
        }

        async function moveWindow(monitor) {
            try {
                await fetch("/api/move_window", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ monitor })
                });
            } catch (e) {
                console.error("Move window failed:", e);
            }
        }

        async function sendChatMessage() {
            const input = document.getElementById("chat-input");
            const text = input.value.trim();
            if (!text) return;
            input.value = "";

            // Append player message immediately
            const chatBox = document.getElementById("chat-messages");
            const tempDiv = document.createElement("div");
            tempDiv.className = "chat-msg player";
            tempDiv.innerHTML = `<strong>Создатель (Вы):</strong> ${escapeHtml(text)}<span class="chat-msg-time">только что</span>`;
            chatBox.appendChild(tempDiv);
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const res = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ session_id: currentSessionId, message: text })
                });
                const data = await res.json();
                await fetchState();
            } catch (e) {
                console.error("Send chat failed:", e);
            }
        }

        function sendQuickChat(text) {
            document.getElementById("chat-input").value = text;
            sendChatMessage();
        }

        function switchTab(tab) {
            document.getElementById("tab-btn-chat").classList.toggle("active", tab === 'chat');
            document.getElementById("tab-btn-history").classList.toggle("active", tab === 'history');
            document.getElementById("tab-content-chat").classList.toggle("active", tab === 'chat');
            document.getElementById("tab-content-history").classList.toggle("active", tab === 'history');
            if (tab === 'history') {
                loadHistory();
            }
        }

        async function loadHistory() {
            const query = document.getElementById("history-search").value;
            const level = parseInt(document.getElementById("history-level-filter").value);
            const status = document.getElementById("history-status-filter").value;

            try {
                const res = await fetch(`/api/history?session_id=${currentSessionId}&query=${encodeURIComponent(query)}&level=${level}&status=${status}`);
                if (!res.ok) return;
                const data = await res.json();
                renderHistory(data.entries || []);
            } catch (e) {
                console.error("Load history error:", e);
            }
        }

        function renderHistory(entries) {
            const list = document.getElementById("history-list");
            if (!entries || entries.length === 0) {
                list.innerHTML = `<div style="color: var(--text-muted); font-size: 12px; text-align: center; padding: 20px;">Записей в истории не найдено.</div>`;
                return;
            }

            list.innerHTML = entries.map(e => `
                <div class="history-entry">
                    <div class="history-header">
                        <span><strong>#${e.id}</strong> | Lvl ${e.level} (${e.goal_shape})</span>
                        <span style="color: ${e.status === 'success' ? 'var(--accent-green)' : 'var(--accent-red)'}; font-weight: bold;">
                            ${e.status.toUpperCase()} (${Math.round(e.execution_latency_ms)}ms)
                        </span>
                        <span>${new Date(e.timestamp * 1000).toLocaleString()}</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-main);">
                        <strong>Решение:</strong> ${escapeHtml(e.thought)}
                    </div>
                    ${e.reasoning_content ? `
                        <details style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">
                            <summary style="cursor: pointer; color: var(--accent-purple);">Показать внутренний CoT (<think>)</summary>
                            <div style="background: #06020a; padding: 6px; border-radius: 4px; font-family: var(--font-mono); margin-top: 4px; white-space: pre-wrap;">${escapeHtml(e.reasoning_content)}</div>
                        </details>
                    ` : ''}
                </div>
            `).join("");
        }

        async function loadSessions() {
            try {
                const res = await fetch("/api/sessions");
                if (!res.ok) return;
                const data = await res.json();
                const sel = document.getElementById("session-select");
                sel.innerHTML = (data.sessions || []).map(s => `
                    <option value="${s.session_id}" ${s.session_id === currentSessionId ? 'selected' : ''}>${s.session_id} (Lvl ${s.level})</option>
                `).join("");
            } catch (e) {}
        }

        function changeSession() {
            currentSessionId = document.getElementById("session-select").value;
            fetchState();
        }

        function escapeHtml(text) {
            if (!text) return "";
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        setInterval(fetchState, 1500);
        loadSessions();
        fetchState();
    </script>
</body>
</html>
"""
