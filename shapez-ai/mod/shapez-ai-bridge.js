// shapez-ai-bridge.js
// High-speed bidirectional Game Bridge for Shapez AI autonomous agent.
// Author: QXIK_mIJ
// License: Apache License 2.0

// @ts-nocheck

const METADATA = {
    website: "https://shapez.io",
    author: "QXIK_mIJ",
    name: "Shapez AI Bridge",
    version: "N-0.3.0",
    id: "shapez-ai-bridge",
    description: "Автономный высокоскоростной двусторонний мост для ИИ-агента Shapez AI (vN-0.3.0).",
    settings: {},
    doesNotAffectSavegame: true,
};

const BRIDGE_WS_URL = "ws://127.0.0.1:8765";
const BRIDGE_RECONNECT_MS = 2000;

class Mod extends shapez.Mod {
    init() {
        if (window.__shapez_ai_bridge_initialized) {
            return;
        }
        window.__shapez_ai_bridge_initialized = true;

        this.ws = null;
        this.isConnected = false;
        this.isAiPaused = true; // Defaults to paused on startup to give player direct control
        this.currentRoot = null;
        this.worldRevision = 1;
        this.isExecutingAiAction = false;
        this.reconnectTimer = null;
        this.lastThroughput = 0;
        this.currentFps = 60;
        this.frameCount = 0;
        this.lastFpsUpdate = performance.now();
        this.aiStatus = "PAUSED";
        this.aiThought = "ИИ в режиме ожидания. Нажмите [▶ Возобновить], чтобы начать.";

        const loopFps = () => {
            this.frameCount++;
            const now = performance.now();
            if (now - this.lastFpsUpdate >= 1000) {
                this.currentFps = Math.round((this.frameCount * 1000) / (now - this.lastFpsUpdate));
                this.frameCount = 0;
                this.lastFpsUpdate = now;
            }
            if (typeof requestAnimationFrame !== "undefined") {
                requestAnimationFrame(loopFps);
            }
        };
        if (typeof requestAnimationFrame !== "undefined") {
            requestAnimationFrame(loopFps);
        }

        window.__shapez_ai_bridge_mod = this;
        this.ensureHud();

        // Периодическая проверка наличия HUD в DOM (защита от затирания движком)
        setInterval(() => {
            this.ensureHud();
        }, 1500);

        this.signals.gameStarted.add(root => {
            this.onGameStarted(root);
        });

        this.signals.stateEntered.add(state => {
            this.ensureHud();
            if (state.constructor.name === "MainMenuState") {
                this.currentRoot = null;
                this.updateHud("MainMenu", "В главном меню");
            }
        });

        this.connectWebSocket();
    }

    /* ------------------------------------------------------------------ */
    /*  WebSocket соединение и протокол                                   */
    /* ------------------------------------------------------------------ */

    connectWebSocket() {
        if (this.ws) {
            try {
                this.ws.close();
            } catch (e) {}
        }

        try {
            this.ws = new WebSocket(BRIDGE_WS_URL);
        } catch (err) {
            this.scheduleReconnect();
            return;
        }

        this.ws.onopen = () => {
            this.isConnected = true;
            this.updateHud("Connected", "Связь с оркестратором установлена");
            this.sendEvent("bridge:connected", { version: METADATA.version });

            // Если игра уже активна, шлем срез
            if (this.currentRoot && this.currentRoot.gameInitialized) {
                this.sendEvent("game:ready", this.collectGameState());
            }
        };

        this.ws.onmessage = event => {
            try {
                const message = JSON.parse(event.data);
                this.handleRpcMessage(message);
            } catch (err) {
                console.error("[ShapezAI] Parse error:", err);
            }
        };

        this.ws.onclose = () => {
            this.isConnected = false;
            this.updateHud("Disconnected", "Связь потеряна. Переподключение...");
            this.scheduleReconnect();
        };

        this.ws.onerror = () => {
            this.isConnected = false;
            this.scheduleReconnect();
        };
    }

    scheduleReconnect() {
        if (this.reconnectTimer) return;
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connectWebSocket();
        }, BRIDGE_RECONNECT_MS);
    }

    sendEvent(eventName, payload) {
        if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }
        try {
            this.ws.send(JSON.stringify({ type: "event", event: eventName, data: payload }));
        } catch (e) {
            console.error("[ShapezAI] sendEvent failed:", e);
        }
    }

    sendRpcResponse(id, result, error = null) {
        if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }
        try {
            this.ws.send(JSON.stringify({ type: "response", id, result, error }));
        } catch (e) {
            console.error("[ShapezAI] sendRpcResponse failed:", e);
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Обработка RPC-команд                                              */
    /* ------------------------------------------------------------------ */

    handleRpcMessage(msg) {
        if (msg.type !== "request") return;
        const { id, action, params } = msg;

        try {
            switch (action) {
                case "ping":
                    this.sendRpcResponse(id, { pong: true, time: Date.now(), fps: this.currentFps });
                    break;

                case "enter_game": {
                    if (this.currentRoot && this.currentRoot.gameInitialized) {
                        this.sendRpcResponse(id, { success: true, alreadyInGame: true, state: this.collectGameState() });
                        break;
                    }
                    const state = this.app && this.app.stateMgr && this.app.stateMgr.currentState;
                    const stateKey = state ? (state.key || (typeof state.getKey === "function" ? state.getKey() : "")) : "";
                    if (state && stateKey === "MainMenuState") {
                        if (params && params.newGame) {
                            const newSave = this.app.savegameMgr.createNewSavegame();
                            state.moveToState("InGameState", { savegame: newSave });
                        } else if (state.savedGames && state.savedGames.length > 0) {
                            state.resumeGame(state.savedGames[0]);
                        } else {
                            state.onPlayButtonClicked();
                        }
                        this.sendRpcResponse(id, { success: true, action: "entering_game" });
                    } else {
                        this.sendRpcResponse(id, { success: false, reason: "Current state is not MainMenuState: " + stateKey });
                    }
                    break;
                }

                case "get_metrics": {
                    this.sendRpcResponse(id, {
                        fps: this.currentFps,
                        throughput: this.lastThroughput,
                        revision: this.worldRevision,
                        inGame: !!(this.currentRoot && this.currentRoot.gameInitialized)
                    });
                    break;
                }

                case "get_game_state":
                    this.sendRpcResponse(id, this.collectGameState());
                    break;

                case "preflight_check":
                    this.sendRpcResponse(id, this.executePreflight(params && params.entities));
                    break;

                case "execute_batch":
                    this.sendRpcResponse(id, this.executeBatch(params && params.entities, params && params.expectedRevision));
                    break;

                case "delete_batch":
                    this.sendRpcResponse(id, this.deleteBatch(params && params.coords));
                    break;

                case "set_hud_status":
                    this.updateHud(params.status || this.aiStatus, params.thought || this.aiThought);
                    this.sendRpcResponse(id, { success: true });
                    break;

                case "get_ai_paused":
                    this.sendRpcResponse(id, { isPaused: this.isAiPaused });
                    break;

                case "set_ai_paused": {
                    this.isAiPaused = !!(params && params.paused);
                    this.updatePauseButton();
                    this.updateHud(this.isAiPaused ? "PAUSED" : "Operating", this.isAiPaused ? "ИИ приостановлен пользователем" : "ИИ активен");
                    this.sendRpcResponse(id, { success: true, isPaused: this.isAiPaused });
                    break;
                }

                case "get_upgrades": {
                    const root = this.currentRoot;
                    if (!root || !root.gameInitialized || !root.hubGoals) {
                        this.sendRpcResponse(id, { success: false, reason: "Game not initialized" });
                        break;
                    }
                    try {
                        const allUpgrades = root.gameMode.getUpgrades();
                        const currentLevels = {};
                        const canUnlock = {};
                        const requirements = {};
                        for (const key in allUpgrades) {
                            const lvl = root.hubGoals.getUpgradeLevel(key);
                            currentLevels[key] = lvl;
                            canUnlock[key] = root.hubGoals.canUnlockUpgrade(key);
                            const tierList = allUpgrades[key];
                            if (tierList && lvl < tierList.length) {
                                requirements[key] = {
                                    tier: lvl + 1,
                                    required: tierList[lvl].required,
                                    improvement: tierList[lvl].improvement
                                };
                            } else {
                                requirements[key] = { maxLevel: true };
                            }
                        }
                        this.sendRpcResponse(id, {
                            success: true,
                            currentLevels,
                            canUnlock,
                            requirements,
                            storedShapes: root.hubGoals.storedShapes || {}
                        });
                    } catch (e) {
                        this.sendRpcResponse(id, { success: false, error: String(e) });
                    }
                    break;
                }

                case "try_unlock_upgrade": {
                    const root = this.currentRoot;
                    if (!root || !root.gameInitialized || !root.hubGoals) {
                        this.sendRpcResponse(id, { success: false, reason: "Game not initialized" });
                        break;
                    }
                    const key = params && params.upgradeKey;
                    if (!key) {
                        this.sendRpcResponse(id, { success: false, reason: "Missing upgradeKey" });
                        break;
                    }
                    try {
                        if (root.hubGoals.canUnlockUpgrade(key)) {
                            const ok = root.hubGoals.tryUnlockUpgrade(key);
                            this.sendRpcResponse(id, { success: ok, newLevel: root.hubGoals.getUpgradeLevel(key) });
                        } else {
                            this.sendRpcResponse(id, { success: false, reason: "Requirements not met for upgrade: " + key });
                        }
                    } catch (e) {
                        this.sendRpcResponse(id, { success: false, error: String(e) });
                    }
                    break;
                }

                case "inspect_tile": {
                    const root = this.currentRoot;
                    if (!root || !root.gameInitialized) {
                        this.sendRpcResponse(id, { success: false, reason: "No root" });
                        break;
                    }
                    const x = params.x;
                    const y = params.y;
                    const lower = root.map.getLowerLayerContentXY(x, y);
                    const ent = root.map.getTileContent(new shapez.Vector(x, y), "regular");
                    let lowerInfo = null;
                    if (lower) {
                        lowerInfo = {
                            type: typeof lower.getItemType === "function" ? lower.getItemType() : "unknown",
                            key: typeof lower.getAsCopyableKey === "function" ? lower.getAsCopyableKey() : ""
                        };
                    }
                    let entInfo = null;
                    if (ent) {
                        const sc = ent.components.StaticMapEntity;
                        const mb = sc ? sc.getMetaBuilding() : null;
                        const belt = ent.components.Belt;
                        const miner = ent.components.Miner;
                        entInfo = {
                            building: mb ? mb.getId() : "unknown",
                            rotation: sc ? sc.rotation : 0,
                            rotationVariant: sc ? sc.getRotationVariant() : 0,
                            direction: belt ? belt.direction : null,
                            minedItem: miner && miner.cachedMinedItem ? (miner.cachedMinedItem.getAsCopyableKey ? miner.cachedMinedItem.getAsCopyableKey() : "yes") : null
                        };
                    }
                    this.sendRpcResponse(id, { x, y, lower: lowerInfo, entity: entInfo });
                    break;
                }

                case "diagnose_factory": {
                    const root = this.currentRoot;
                    if (!root || !root.gameInitialized) {
                        this.sendRpcResponse(id, { success: false, reason: "Game not initialized" });
                        break;
                    }
                    const hubGoals = root.hubGoals;
                    const currentGoal = hubGoals ? hubGoals.currentGoal : null;
                    const goalDef = currentGoal ? currentGoal.definition : null;
                    const goalHash = goalDef ? (typeof goalDef.getHash === "function" ? goalDef.getHash() : String(goalDef)) : "";
                    
                    let currentRate = 0;
                    if (goalDef && root.productionAnalytics) {
                        currentRate = root.productionAnalytics.getCurrentShapeRateRaw(
                            shapez.enumAnalyticsDataSource.delivered,
                            goalDef
                        ) || 0;
                    }

                    const entities = root.entityMgr ? root.entityMgr.entities : [];
                    const miners = [];
                    const processors = [];
                    const hubEntrances = [];
                    let beltCount = 0;

                    for (let i = 0; i < entities.length; i++) {
                        const ent = entities[i];
                        if (ent.destroyed || ent.queuedForDestroy) continue;
                        const sc = ent.components && ent.components.StaticMapEntity;
                        if (!sc) continue;
                        const meta = sc.getMetaBuilding();
                        const bId = meta ? meta.getId() : "";
                        const origin = sc.origin;

                        if (bId === "miner") {
                            const minerComp = ent.components.Miner;
                            let minedItemKey = null;
                            if (minerComp && minerComp.cachedMinedItem) {
                                minedItemKey = typeof minerComp.cachedMinedItem.getAsCopyableKey === "function"
                                    ? minerComp.cachedMinedItem.getAsCopyableKey()
                                    : String(minerComp.cachedMinedItem);
                            }
                            miners.push({
                                x: origin.x,
                                y: origin.y,
                                rotation: sc.rotation,
                                minedItem: minedItemKey
                            });
                        } else if (bId === "cutter" || bId === "cutter_mirrored" || bId === "rotater" || bId === "stacker" || bId === "painter" || bId === "mixer" || bId === "mixerMirrored") {
                            processors.push({
                                building: bId,
                                x: origin.x,
                                y: origin.y,
                                rotation: sc.rotation
                            });
                        } else if (bId === "belt") {
                            beltCount++;
                            const rot = sc.rotation;
                            let targetX = origin.x;
                            let targetY = origin.y;
                            if (rot === 0) targetY -= 1;
                            else if (rot === 90) targetX += 1;
                            else if (rot === 180) targetY += 1;
                            else if (rot === 270) targetX -= 1;

                            if (targetX >= -2 && targetX <= 1 && targetY >= -2 && targetY <= 1) {
                                hubEntrances.push({
                                    beltX: origin.x,
                                    beltY: origin.y,
                                    targetX: targetX,
                                    targetY: targetY,
                                    rotation: rot
                                });
                            }
                        }
                    }

                    this.sendRpcResponse(id, {
                        success: true,
                        level: hubGoals ? hubGoals.level : 1,
                        goal: {
                            shape: goalHash,
                            delivered: hubGoals ? hubGoals.getCurrentGoalDelivered() : 0,
                            required: currentGoal ? currentGoal.required : 0,
                            throughput: currentRate
                        },
                        miners: miners,
                        processors: processors,
                        beltCount: beltCount,
                        hubEntrances: hubEntrances,
                        totalEntities: entities.length
                    });
                    break;
                }

                case "eval_code": {
                    try {
                        const fn = new Function("root", "bridge", params.code);
                        const res = fn(this.currentRoot, this);
                        this.sendRpcResponse(id, { success: true, result: res });
                    } catch (err) {
                        this.sendRpcResponse(id, { success: false, error: String(err) });
                    }
                    break;
                }

                default:
                    this.sendRpcResponse(id, null, "Unknown action: " + action);
            }
        } catch (ex) {
            console.error("[ShapezAI] RPC execution error:", ex);
            this.sendRpcResponse(id, null, String(ex && ex.message ? ex.message : ex));
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Хуки жизненного цикла игры                                         */
    /* ------------------------------------------------------------------ */

    onGameStarted(root) {
        this.currentRoot = root;
        this.worldRevision = 1;
        this.updateHud("InGame", "Мир загружен. Ожидание команд ИИ.");

        // Подписка на уничтожение сущностей
        root.signals.entityDestroyed.add(entity => {
            this.onEntityDestroyed(entity);
        });

        // Завершение сюжетного уровня
        root.signals.storyGoalCompleted.add((level, key) => {
            this.sendEvent("event:goal_completed", { level, key, state: this.collectGameState() });
        });

        // Доставка целевой фигуры
        root.signals.shapeDelivered.add(shapeDef => {
            const hash = shapeDef ? (typeof shapeDef.getHash === "function" ? shapeDef.getHash() : shapeDef.toString()) : "";
            this.sendEvent("event:shape_delivered", { shape: hash });
        });

        // Покупка улучшений
        if (root.signals.upgradePurchased) {
            root.signals.upgradePurchased.add(upgradeKey => {
                this.sendEvent("event:upgrade_purchased", {
                    upgrade: upgradeKey,
                    level: root.hubGoals ? root.hubGoals.getUpgradeLevel(upgradeKey) : 0
                });
            });
        }

        // Heartbeat телеметрии производства (раз в 1.5 секунды)
        setInterval(() => {
            if (!this.currentRoot || !this.currentRoot.gameInitialized) return;
            const hubGoals = this.currentRoot.hubGoals;
            const currentGoal = hubGoals && hubGoals.currentGoal;
            let rate = 0;
            let delivered = 0;
            let required = 0;
            let goalShape = "";
            let level = hubGoals ? hubGoals.level : 1;
            if (currentGoal && currentGoal.definition && this.currentRoot.productionAnalytics) {
                rate = this.currentRoot.productionAnalytics.getCurrentShapeRateRaw(
                    shapez.enumAnalyticsDataSource.delivered,
                    currentGoal.definition
                ) || 0;
                delivered = hubGoals.getCurrentGoalDelivered() || 0;
                required = currentGoal.required || 0;
                goalShape = typeof currentGoal.definition.getHash === "function" ? currentGoal.definition.getHash() : String(currentGoal.definition);
            }
            this.lastThroughput = rate;
            this.sendEvent("event:throughput_heartbeat", {
                throughput: rate,
                delivered: delivered,
                required: required,
                level: level,
                goalShape: goalShape,
                fps: this.currentFps
            });
        }, 1500);

        if (this.isConnected) {
            this.sendEvent("game:ready", this.collectGameState());
        }
    }

    onEntityDestroyed(entity) {
        if (!entity || this.isExecutingAiAction) {
            // Если удалено самим ИИ при деконструкции/откате — не считаем ручным вмешательством
            return;
        }

        const staticComp = entity.components && entity.components.StaticMapEntity;
        if (!staticComp) return;

        this.worldRevision++;
        const meta = staticComp.getMetaBuilding();
        const buildingId = meta ? meta.getId() : "unknown";
        const origin = staticComp.origin;

        this.sendEvent("event:entity_destroyed", {
            manual: true,
            building: buildingId,
            x: origin.x,
            y: origin.y,
            rotation: staticComp.rotation,
            layer: entity.layer,
            worldRevision: this.worldRevision,
        });

        this.updateHud("Intervention", `Обнаружено ручное удаление: ${buildingId} в (${origin.x}, ${origin.y})`);
    }

    /* ------------------------------------------------------------------ */
    /*  Сбор среза состояния мира (Game State Collection)                 */
    /* ------------------------------------------------------------------ */

    collectGameState() {
        const root = this.currentRoot;
        if (!root || !root.gameInitialized) {
            return { ready: false, revision: this.worldRevision };
        }

        const hubGoals = root.hubGoals;
        const currentGoal = hubGoals.currentGoal;
        const goalDef = currentGoal ? currentGoal.definition : null;
        const goalHash = goalDef ? (typeof goalDef.getHash === "function" ? goalDef.getHash() : String(goalDef)) : "";

        // Разблокированные здания
        const unlocked = [];
        const toolbar = root.hud && root.hud.parts && root.hud.parts.buildingsToolbar;
        if (toolbar && toolbar.buildingHandles) {
            for (const bId in toolbar.buildingHandles) {
                if (!toolbar.buildingHandles[bId].locked) {
                    unlocked.push(bId);
                }
            }
        }

        // Поиск залежей ресурсов в радиусе вокруг Хаба (до 8 чанков)
        const patches = [];
        const scanRadiusChunks = 8;
        for (let cx = -scanRadiusChunks; cx <= scanRadiusChunks; cx++) {
            for (let cy = -scanRadiusChunks; cy <= scanRadiusChunks; cy++) {
                const chunk = root.map.getChunk(cx, cy, true);
                if (chunk && chunk.patches) {
                    for (let i = 0; i < chunk.patches.length; i++) {
                        const patch = chunk.patches[i];
                        const item = patch.item;
                        if (!item) continue;
                        const itemType = typeof item.getItemType === "function" ? item.getItemType() : (item.id || "shape");
                        let itemPayload = "";
                        if (typeof item.getAsCopyableKey === "function") {
                            itemPayload = item.getAsCopyableKey();
                        } else if (item.definition && typeof item.definition.getHash === "function") {
                            itemPayload = item.definition.getHash();
                        } else if (item.color) {
                            itemPayload = item.color;
                        } else if (typeof item.serialize === "function") {
                            itemPayload = item.serialize();
                        }

                        let bestTileX = Math.round(chunk.tileX + patch.pos.x);
                        let bestTileY = Math.round(chunk.tileY + patch.pos.y);
                        if (chunk.lowerLayer) {
                            const localX = Math.max(0, Math.min(15, Math.round(patch.pos.x)));
                            const localY = Math.max(0, Math.min(15, Math.round(patch.pos.y)));
                            if (chunk.lowerLayer[localX] && chunk.lowerLayer[localX][localY]) {
                                bestTileX = chunk.tileX + localX;
                                bestTileY = chunk.tileY + localY;
                            } else {
                                findTile:
                                for (let r = 1; r <= 8; r++) {
                                    for (let dx = -r; dx <= r; dx++) {
                                        for (let dy = -r; dy <= r; dy++) {
                                            const lx = localX + dx;
                                            const ly = localY + dy;
                                            if (lx >= 0 && lx < 16 && ly >= 0 && ly < 16 && chunk.lowerLayer[lx] && chunk.lowerLayer[lx][ly]) {
                                                bestTileX = chunk.tileX + lx;
                                                bestTileY = chunk.tileY + ly;
                                                break findTile;
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        patches.push({
                            chunkX: cx,
                            chunkY: cy,
                            tileX: bestTileX,
                            tileY: bestTileY,
                            type: itemType,
                            item: itemPayload,
                            size: patch.size,
                        });
                    }
                }
            }
        }

        // Список существующих зданий в активной зоне
        const activeEntities = [];
        for (let i = 0; i < root.entityMgr.entities.length; i++) {
            const ent = root.entityMgr.entities[i];
            if (ent.destroyed || ent.queuedForDestroy) continue;
            const sc = ent.components.StaticMapEntity;
            if (sc) {
                const mb = sc.getMetaBuilding();
                activeEntities.push({
                    uid: ent.uid,
                    building: mb ? mb.getId() : "unknown",
                    x: sc.origin.x,
                    y: sc.origin.y,
                    rotation: sc.rotation,
                    rotationVariant: sc.getRotationVariant(),
                    variant: sc.getVariant(),
                    layer: ent.layer,
                });
            }
        }

        return {
            ready: true,
            revision: this.worldRevision,
            fps: this.currentFps,
            gameTime: root.time.now(),
            level: hubGoals.level,
            goal: {
                shape: goalHash,
                required: currentGoal ? currentGoal.required : 0,
                delivered: hubGoals.getCurrentGoalDelivered(),
                throughputOnly: currentGoal ? currentGoal.throughputOnly : false,
            },
            hub: {
                bounds: { x: -2, y: -2, w: 4, h: 4 },
                // 16 входов в Хаб:
                // Верх (y = -2, вход с y = -3, направление вниз: enumDirection.bottom)
                // Низ (y = 1, вход с y = 2, направление вверх: enumDirection.top)
                // Лево (x = -2, вход с x = -3, направление вправо: enumDirection.right)
                // Право (x = 1, вход с x = 2, направление влево: enumDirection.left)
            },
            unlockedBuildings: unlocked,
            patches,
            entitiesCount: activeEntities.length,
            entities: activeEntities,
        };
    }

    /* ------------------------------------------------------------------ */
    /*  Безопасное выполнение: Preflight и Batch Execution                */
    /* ------------------------------------------------------------------ */

    executePreflight(entities) {
        const root = this.currentRoot;
        if (!root || !root.gameInitialized) {
            return { valid: false, error: "Game not initialized" };
        }
        if (!Array.isArray(entities) || entities.length === 0) {
            return { valid: true, count: 0 };
        }

        if (root.entityMgr && root.entityMgr.destroyList && root.entityMgr.destroyList.length > 0) {
            root.entityMgr.processDestroyList();
        }

        const toolbar = root.hud && root.hud.parts && root.hud.parts.buildingsToolbar;

        for (let i = 0; i < entities.length; i++) {
            const spec = entities[i];
            const metaBuilding = shapez.gMetaBuildingRegistry.findById(spec.building);
            if (!metaBuilding) {
                return { valid: false, failedIndex: i, reason: `Unknown building: ${spec.building}` };
            }

            // Проверка доступности по тулбару
            if (toolbar && toolbar.buildingHandles && toolbar.buildingHandles[spec.building]) {
                if (toolbar.buildingHandles[spec.building].locked) {
                    return { valid: false, failedIndex: i, reason: `Building ${spec.building} is locked` };
                }
            }

            // Проверка зоны Хаба: нельзя строить поверх самого Хаба [-2..1, -2..1]
            if (spec.x >= -2 && spec.x <= 1 && spec.y >= -2 && spec.y <= 1) {
                return { valid: false, failedIndex: i, reason: `Cannot build on Hub area at (${spec.x}, ${spec.y})` };
            }

            const rot = typeof spec.rotation === "number" ? spec.rotation : 0;
            const origRot = typeof spec.originalRotation === "number" ? spec.originalRotation : rot;
            const rotVar = typeof spec.rotationVariant === "number" ? spec.rotationVariant : 0;

            // Создаем временную сущность для проверки checkCanPlaceEntity
            const tempEntity = metaBuilding.createEntity({
                root,
                origin: new shapez.Vector(spec.x, spec.y),
                rotation: rot,
                originalRotation: origRot,
                rotationVariant: rotVar,
                variant: spec.variant || shapez.defaultBuildingVariant,
            });

            if (!root.logic.checkCanPlaceEntity(tempEntity, { allowReplaceBuildings: false })) {
                return {
                    valid: false,
                    failedIndex: i,
                    reason: `Tile occupied or invalid at (${spec.x}, ${spec.y}) for ${spec.building}`,
                };
            }
        }

        return { valid: true, count: entities.length };
    }

    executeBatch(entities, expectedRevision = null) {
        const root = this.currentRoot;
        if (!root || !root.gameInitialized) {
            return { success: false, error: "Game not initialized" };
        }

        if (expectedRevision !== null && expectedRevision !== this.worldRevision) {
            return {
                success: false,
                error: "Stale world revision",
                currentRevision: this.worldRevision,
                expectedRevision,
            };
        }

        const t0 = performance.now();

        // Фаза 1: Предварительная сухая проверка
        const preCheck = this.executePreflight(entities);
        if (!preCheck.valid) {
            return { success: false, error: "preflight_failed", detail: preCheck };
        }

        // Фаза 2: Пакетное размещение с возможностью полного отката
        const placed = [];
        let executionError = null;

        root.logic.performBulkOperation(() => {
            this.isExecutingAiAction = true;
            try {
                for (let i = 0; i < entities.length; i++) {
                    const spec = entities[i];
                    const metaBuilding = shapez.gMetaBuildingRegistry.findById(spec.building);

                    const rot = typeof spec.rotation === "number" ? spec.rotation : 0;
                    const origRot = typeof spec.originalRotation === "number" ? spec.originalRotation : rot;
                    const rotVar = typeof spec.rotationVariant === "number" ? spec.rotationVariant : 0;

                    const entity = root.logic.tryPlaceBuilding({
                        origin: new shapez.Vector(spec.x, spec.y),
                        rotation: rot,
                        originalRotation: origRot,
                        rotationVariant: rotVar,
                        variant: spec.variant || shapez.defaultBuildingVariant,
                        building: metaBuilding,
                    });

                    if (!entity) {
                        executionError = `Placement returned null at index ${i} (${spec.building} at ${spec.x}, ${spec.y})`;
                        break;
                    }
                    placed.push(entity);
                }
            } catch (ex) {
                executionError = String(ex);
            } finally {
                this.isExecutingAiAction = false;
            }
        });

        // Откат в случае частичного сбоя
        if (executionError) {
            root.logic.performBulkOperation(() => {
                this.isExecutingAiAction = true;
                try {
                    for (let i = 0; i < placed.length; i++) {
                        root.logic.tryDeleteBuilding(placed[i]);
                    }
                } finally {
                    this.isExecutingAiAction = false;
                }
            });

            if (root.entityMgr && root.entityMgr.destroyList && root.entityMgr.destroyList.length > 0) {
                root.entityMgr.processDestroyList();
            }

            const execMs = Math.round((performance.now() - t0) * 100) / 100;
            return {
                success: false,
                error: "execution_failed",
                detail: executionError,
                rolledBackCount: placed.length,
                executionTimeMs: execMs,
            };
        }

        const execMs = Math.round((performance.now() - t0) * 100) / 100;
        this.worldRevision++;
        this.updateHud("Operating", `Успешно возведено ${placed.length} объектов (${execMs}мс). Ревизия: ${this.worldRevision}`);
        return {
            success: true,
            placedCount: placed.length,
            revision: this.worldRevision,
            executionTimeMs: execMs,
        };
    }

    deleteBatch(coords) {
        const root = this.currentRoot;
        if (!root || !root.gameInitialized) {
            return { success: false, error: "Game not initialized" };
        }
        if (!Array.isArray(coords) || coords.length === 0) {
            return { success: true, count: 0 };
        }

        const t0 = performance.now();
        let deletedCount = 0;
        root.logic.performBulkOperation(() => {
            this.isExecutingAiAction = true;
            try {
                for (let i = 0; i < coords.length; i++) {
                    const c = coords[i];
                    const targetX = c.x;
                    const targetY = c.y;
                    let ent = root.map.getLayerContentXY(targetX, targetY, c.layer || "regular");
                    if (!ent) {
                        ent = root.entityMgr.entities.find(e => {
                            const sc = e.components.StaticMapEntity;
                            return sc && sc.origin.x === targetX && sc.origin.y === targetY;
                        });
                    }
                    if (ent && root.logic.canDeleteBuilding(ent)) {
                        if (root.logic.tryDeleteBuilding(ent)) {
                            deletedCount++;
                        }
                    }
                }
            } finally {
                this.isExecutingAiAction = false;
            }
        });

        const execMs = Math.round((performance.now() - t0) * 100) / 100;
        this.worldRevision++;
        return { success: true, deletedCount, revision: this.worldRevision, executionTimeMs: execMs };
    }

    /* ------------------------------------------------------------------ */
    /*  HUD Overlay (Dark Violet Aesthetic & Draggable)                   */
    /* ------------------------------------------------------------------ */

    injectHudStyles() {
        if (document.getElementById("shapez-ai-hud-styles")) return;
        const css = `
            #shapez-ai-hud {
                position: fixed;
                top: 14px;
                left: 50%;
                transform: translateX(-50%);
                background: linear-gradient(135deg, rgba(22, 12, 36, 0.96) 0%, rgba(36, 16, 56, 0.96) 100%);
                border: 1.5px solid rgba(168, 85, 247, 0.75);
                border-radius: 10px;
                padding: 7px 16px;
                color: #e0aaff;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
                font-size: 13px;
                z-index: 9999999;
                pointer-events: auto;
                user-select: none;
                box-shadow: 0 8px 32px rgba(10, 4, 20, 0.85), 0 0 16px rgba(157, 78, 221, 0.35);
                display: flex;
                align-items: center;
                gap: 12px;
                backdrop-filter: blur(12px);
                transition: box-shadow 0.2s ease, border-color 0.2s ease;
            }
            #shapez-ai-hud.is-dragging {
                box-shadow: 0 12px 40px rgba(10, 4, 20, 0.95), 0 0 25px rgba(168, 85, 247, 0.6);
                border-color: #c77dff;
                cursor: grabbing !important;
            }
            #shapez-ai-hud .ai-drag-handle {
                cursor: grab;
                color: #a855f7;
                font-size: 16px;
                line-height: 1;
                padding: 2px 6px;
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s, color 0.2s;
            }
            #shapez-ai-hud .ai-drag-handle:hover {
                background: rgba(168, 85, 247, 0.25);
                color: #f1e4ff;
            }
            #shapez-ai-hud .ai-indicator {
                width: 10px;
                height: 10px;
                min-width: 10px;
                border-radius: 50%;
                background: #ff0055;
                box-shadow: 0 0 10px #ff0055;
                transition: background 0.3s, box-shadow 0.3s;
            }
            #shapez-ai-hud .ai-indicator.connected {
                background: #00ff88;
                box-shadow: 0 0 10px #00ff88;
            }
            #shapez-ai-hud .ai-title {
                font-weight: 700;
                color: #d8b4fe;
                letter-spacing: 0.5px;
                font-size: 13px;
                white-space: nowrap;
            }
            #shapez-ai-hud .hud-btn {
                background: rgba(157, 78, 221, 0.3);
                border: 1px solid #9d4edd;
                color: #f1e4ff;
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
                outline: none;
                pointer-events: auto;
                white-space: nowrap;
            }
            #shapez-ai-hud .hud-btn:hover {
                background: rgba(157, 78, 221, 0.6);
                border-color: #c77dff;
                transform: translateY(-1px);
            }
            #shapez-ai-hud .hud-btn:active {
                transform: translateY(0);
            }
            #shapez-ai-hud .hud-btn.paused {
                background: rgba(255, 183, 3, 0.25);
                border-color: #ffb703;
                color: #ffb703;
            }
            #shapez-ai-hud .hud-btn.paused:hover {
                background: rgba(255, 183, 3, 0.45);
            }
            #shapez-ai-hud .hud-btn-icon {
                background: transparent;
                border: none;
                color: #9d4edd;
                font-size: 14px;
                cursor: pointer;
                padding: 2px 6px;
                border-radius: 4px;
                line-height: 1;
                transition: all 0.2s;
            }
            #shapez-ai-hud .hud-btn-icon:hover {
                background: rgba(157, 78, 221, 0.25);
                color: #e0aaff;
            }
            #shapez-ai-hud .ai-status-badge {
                padding: 2px 7px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
                background: rgba(157, 78, 221, 0.2);
                border: 1px solid rgba(157, 78, 221, 0.4);
                color: #c77dff;
                white-space: nowrap;
            }
            #shapez-ai-hud .ai-fps-badge {
                color: #67e8f9;
                font-size: 11px;
                font-weight: 700;
                font-family: monospace;
                white-space: nowrap;
            }
            #shapez-ai-hud .ai-thought {
                color: #f1f1f1;
                font-size: 12px;
                max-width: 440px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                background: rgba(0, 0, 0, 0.25);
                padding: 3px 8px;
                border-radius: 4px;
                border-left: 2px solid #a855f7;
            }
            #shapez-ai-hud.collapsed .ai-thought,
            #shapez-ai-hud.collapsed .ai-status-badge,
            #shapez-ai-hud.collapsed .ai-fps-badge {
                display: none !important;
            }
        `;
        const style = document.createElement("style");
        style.id = "shapez-ai-hud-styles";
        style.textContent = css;
        document.head.appendChild(style);
    }

    setupHudDraggable(hud) {
        let isDragging = false;
        let startX = 0;
        let startY = 0;
        let initialLeft = 0;
        let initialTop = 0;

        const onMouseDown = (e) => {
            if (e.target.closest("button") || e.target.closest("input")) return;
            isDragging = true;
            hud.classList.add("is-dragging");
            const rect = hud.getBoundingClientRect();
            hud.style.transform = "none";
            hud.style.left = `${rect.left}px`;
            hud.style.top = `${rect.top}px`;
            initialLeft = rect.left;
            initialTop = rect.top;
            startX = e.clientX;
            startY = e.clientY;
            document.addEventListener("mousemove", onMouseMove, { passive: false });
            document.addEventListener("mouseup", onMouseUp);
            e.preventDefault();
        };

        const onMouseMove = (e) => {
            if (!isDragging) return;
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            let newLeft = initialLeft + deltaX;
            let newTop = initialTop + deltaY;
            const rect = hud.getBoundingClientRect();
            const minX = 8;
            const maxX = Math.max(8, window.innerWidth - rect.width - 8);
            const minY = 8;
            const maxY = Math.max(8, window.innerHeight - rect.height - 8);
            newLeft = Math.max(minX, Math.min(maxX, newLeft));
            newTop = Math.max(minY, Math.min(maxY, newTop));
            hud.style.left = `${newLeft}px`;
            hud.style.top = `${newTop}px`;
            e.preventDefault();
        };

        const onMouseUp = () => {
            if (!isDragging) return;
            isDragging = false;
            hud.classList.remove("is-dragging");
            document.removeEventListener("mousemove", onMouseMove);
            document.removeEventListener("mouseup", onMouseUp);
            const rect = hud.getBoundingClientRect();
            try {
                localStorage.setItem("shapez_ai_hud_pos", JSON.stringify({
                    left: Math.round(rect.left),
                    top: Math.round(rect.top)
                }));
            } catch (err) {}
        };

        const handle = hud.querySelector(".ai-drag-handle");
        if (handle) {
            handle.addEventListener("mousedown", onMouseDown);
        }
        hud.addEventListener("mousedown", onMouseDown);
    }

    restoreHudPosition(hud) {
        try {
            const saved = localStorage.getItem("shapez_ai_hud_pos");
            if (saved) {
                const pos = JSON.parse(saved);
                if (typeof pos.left === "number" && typeof pos.top === "number") {
                    const rect = hud.getBoundingClientRect();
                    const w = rect.width || 500;
                    const h = rect.height || 45;
                    const clampedLeft = Math.max(8, Math.min(window.innerWidth - w - 8, pos.left));
                    const clampedTop = Math.max(8, Math.min(window.innerHeight - h - 8, pos.top));
                    hud.style.transform = "none";
                    hud.style.left = `${clampedLeft}px`;
                    hud.style.top = `${clampedTop}px`;
                    return;
                }
            }
        } catch (e) {}
        hud.style.top = "14px";
        hud.style.left = "50%";
        hud.style.transform = "translateX(-50%)";
    }

    toggleCollapse(hud) {
        hud.classList.toggle("collapsed");
        const isCollapsed = hud.classList.contains("collapsed");
        const btn = document.getElementById("shapez-ai-collapse-btn");
        if (btn) {
            btn.textContent = isCollapsed ? "□" : "─";
            btn.title = isCollapsed ? "Развернуть HUD" : "Свернуть HUD";
        }
        try {
            localStorage.setItem("shapez_ai_hud_collapsed", isCollapsed ? "true" : "false");
        } catch (e) {}
    }

    createHudOverlay() {
        if (document.getElementById("shapez-ai-hud")) return;
        const hud = document.createElement("div");
        hud.id = "shapez-ai-hud";
        hud.innerHTML = `
            <div class="ai-drag-handle" title="Зажмите и перетащите HUD в любое место экрана">⠿</div>
            <div class="ai-indicator" id="shapez-ai-indicator"></div>
            <div class="ai-title">SHAPEZ AI N-0.3.0</div>
            <button id="shapez-ai-pause-btn" class="hud-btn paused" title="Управление активностью автономного агента">▶ Возобновить ИИ</button>
            <div id="shapez-ai-status" class="ai-status-badge">PAUSED</div>
            <div id="shapez-ai-fps" class="ai-fps-badge">-- FPS</div>
            <div class="ai-thought" id="shapez-ai-thought" title="Текущая мысль ИИ">ИИ в режиме ожидания. Нажмите [▶], чтобы запустить.</div>
            <button id="shapez-ai-collapse-btn" class="hud-btn-icon" title="Свернуть HUD">─</button>
        `;
        document.body.appendChild(hud);

        this.restoreHudPosition(hud);
        this.setupHudDraggable(hud);

        const btn = document.getElementById("shapez-ai-pause-btn");
        if (btn) {
            btn.addEventListener("click", e => {
                e.stopPropagation();
                e.preventDefault();
                this.togglePause();
            });
        }

        const collapseBtn = document.getElementById("shapez-ai-collapse-btn");
        if (collapseBtn) {
            collapseBtn.addEventListener("click", e => {
                e.stopPropagation();
                e.preventDefault();
                this.toggleCollapse(hud);
            });
        }
    }

    ensureHud() {
        this.injectHudStyles();
        let hud = document.getElementById("shapez-ai-hud");
        if (!hud) {
            this.createHudOverlay();
            hud = document.getElementById("shapez-ai-hud");
        }
        if (hud) {
            try {
                if (localStorage.getItem("shapez_ai_hud_collapsed") === "true") {
                    hud.classList.add("collapsed");
                    const btn = document.getElementById("shapez-ai-collapse-btn");
                    if (btn) {
                        btn.textContent = "□";
                        btn.title = "Развернуть HUD";
                    }
                }
            } catch (e) {}
            this.updatePauseButton();
            this.updateHud(this.aiStatus, this.aiThought);
        }
    }

    togglePause() {
        this.isAiPaused = !this.isAiPaused;
        this.updatePauseButton();
        if (this.isAiPaused) {
            this.updateHud("PAUSED", "ИИ приостановлен пользователем");
        } else {
            this.updateHud("Operating", "Возобновление работы ИИ...");
        }
        this.sendEvent("event:pause_toggle", { paused: this.isAiPaused });
    }

    updatePauseButton() {
        const btn = document.getElementById("shapez-ai-pause-btn");
        if (!btn) return;
        if (this.isAiPaused) {
            btn.className = "hud-btn paused";
            btn.textContent = "▶ Возобновить ИИ";
        } else {
            btn.className = "hud-btn";
            btn.textContent = "⏸ Пауза ИИ";
        }
    }

    updateHud(status, thought) {
        this.aiStatus = status || this.aiStatus;
        this.aiThought = thought || this.aiThought;

        let hud = document.getElementById("shapez-ai-hud");
        if (!hud) {
            this.ensureHud();
            hud = document.getElementById("shapez-ai-hud");
        }

        const ind = document.getElementById("shapez-ai-indicator");
        const st = document.getElementById("shapez-ai-status");
        const th = document.getElementById("shapez-ai-thought");
        const fpsElem = document.getElementById("shapez-ai-fps");

        if (ind) {
            if (this.isConnected) {
                ind.classList.add("connected");
            } else {
                ind.classList.remove("connected");
            }
        }
        if (st) st.textContent = this.aiStatus;
        if (th) {
            th.textContent = this.aiThought;
            th.title = this.aiThought;
        }
        if (fpsElem) fpsElem.textContent = `${this.currentFps} FPS`;
    }
}
