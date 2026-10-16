const fs = require('fs');
const path = require('path');

// Compression routines from bundle.js
const ch = String.fromCharCode;
const a_x64 = {};
const o_x64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-$';

function _compress(e, t, r) {
    if (null == e) return '';
    var i, o, a, s = {}, l = {}, c = '', u = '', h = '', d = 2, g = 3, A = 2, p = [], f = 0, m = 0;
    var n = Object.prototype.hasOwnProperty;
    for (a = 0; a < e.length; a += 1) {
        if (c = e.charAt(a), n.call(s, c) || (s[c] = g++, l[c] = !0), u = h + c, n.call(s, u)) {
            h = u;
        } else {
            if (n.call(l, h)) {
                if (h.charCodeAt(0) < 256) {
                    for (i = 0; i < A; i++) f <<= 1, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++;
                    for (o = h.charCodeAt(0), i = 0; i < 8; i++) f = f << 1 | 1 & o, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++, o >>= 1;
                } else {
                    for (o = 1, i = 0; i < A; i++) f = f << 1 | o, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++, o = 0;
                    for (o = h.charCodeAt(0), i = 0; i < 16; i++) f = f << 1 | 1 & o, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++, o >>= 1;
                }
                0 == --d && (d = Math.pow(2, A), A++), delete l[h];
            } else {
                for (o = s[h], i = 0; i < A; i++) f = f << 1 | 1 & o, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++, o >>= 1;
            }
            0 == --d && (d = Math.pow(2, A), A++), s[u] = g++, h = String(c);
        }
    }
    if ('' !== h) {
        if (n.call(l, h)) {
            if (h.charCodeAt(0) < 256) {
                for (i = 0; i < A; i++) f <<= 1, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++;
                for (o = h.charCodeAt(0), i = 0; i < 8; i++) f = f << 1 | 1 & o, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++, o >>= 1;
            } else {
                for (o = 1, i = 0; i < A; i++) f = f << 1 | o, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++, o = 0;
                for (o = h.charCodeAt(0), i = 0; i < 16; i++) f = f << 1 | 1 & o, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++, o >>= 1;
            }
            0 == --d && (d = Math.pow(2, A), A++), delete l[h];
        } else {
            for (o = s[h], i = 0; i < A; i++) f = f << 1 | 1 & o, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++, o >>= 1;
        }
        0 == --d && (d = Math.pow(2, A), A++);
    }
    for (o = 2, i = 0; i < A; i++) f = f << 1 | 1 & o, m == t - 1 ? (m = 0, p.push(r(f)), f = 0) : m++, o >>= 1;
    for (; ;) {
        if (f <<= 1, m == t - 1) {
            p.push(r(f));
            break;
        }
        m++;
    }
    return p.join('');
}

function compressX64(e) {
    return null == e ? '' : _compress(e, 6, function (idx) { return o_x64.charAt(idx); });
}

function encodeBP(entities) {
    const payload = {
        f: 1,
        l: "regular",
        e: entities
    };
    return "[SHAPEZ-BP1:" + compressX64(JSON.stringify(payload)) + "]";
}

// -----------------------------------------------------------------------------
// DESIGN 1: THE PRO DUAL-WING WHITE DYE MODULE (12 tiles wide)
// Width: X = 0..11 (12 tiles)
// Height: Y = 0..27 (28 tiles)
//
// Left output: X=0 (merger chain moving North)
// Left Mixers: X=1 (rot 270, facing West into X=0)
// Center Left Input: X=2, X=3, X=4
// Center Right Input: X=7, X=8, X=9
// Right Mixers: X=10 (rot 90, facing East into X=11)
// Right output: X=11 (merger chain moving North)
//
// Stage 1 (South): Y=14..25 (6 rows of paired mixers = 12 mixers for Red+Green -> Yellow)
// Stage 2 (North): Y=2..13  (6 rows of paired mixers = 12 mixers for Yellow+Blue -> White)
// Balancer & Port Top: Y=0..1 (balanced outputs)
// Port Bottom: Y=26..27 (standard inputs for Red, Green, Blue)
// -----------------------------------------------------------------------------

function buildDualWingModule() {
    const entities = [];

    function add(b, v, w, x, y, r) {
        entities.push({ b, v, w, x, y, r, o: r });
    }

    // STAGE 2: Yellow + Blue -> White (Rows Y = 2 to 13, dy=2 -> 6 rows)
    for (let i = 0; i < 6; ++i) {
        const y = 2 + i * 2;

        // Left Wing Mixer (rot 270, facing West): occupies (1, y) and (1, y+1)
        add("mixer", "default", 0, 1, y, 270);
        // Left output merger at (0, y), belt at (0, y+1)
        add("balancer", "merger", 0, 0, y, 0); // merges from East (1, y) going North
        add("belt", "default", 0, 0, y + 1, 0);

        // Right Wing Mixer (rot 90, facing East): occupies (10, y) and (10, y+1)
        add("mixer", "default", 0, 10, y, 90);
        // Right output merger-inverse at (11, y), belt at (11, y+1)
        add("balancer", "merger-inverse", 0, 11, y, 0); // merges from West (10, y) going North
        add("belt", "default", 0, 11, y + 1, 0);

        // Inputs for Stage 2:
        // Slot 0 (Yellow from central Yellow bus)
        // Slot 1 (Blue from Blue bus)
        // Blue is in outer spine (X=4 and X=7):
        add("balancer", "splitter-inverse", 0, 4, y, 0); // splits West to (2, y)
        add("belt", "default", 0, 4, y + 1, 0);
        add("balancer", "splitter", 0, 7, y, 0); // splits East to (9, y)
        add("belt", "default", 0, 7, y + 1, 0);

        // Feed to mixer inputs:
        // Left side inputs into (1, y) and (1, y+1) come from (2, y) and (2, y+1):
        add("belt", "default", 0, 2, y, 270); // Blue entering from East
        add("underground_belt", "default", 1, 2, y + 1, 270); // Yellow exit from underground facing West
        add("underground_belt", "default", 0, 5, y + 1, 270); // Yellow entry at (5, y+1) facing West

        // Right side inputs into (10, y) and (10, y+1) come from (9, y) and (9, y+1):
        add("belt", "default", 0, 9, y, 90); // Blue entering from West
        add("underground_belt", "default", 1, 9, y + 1, 90); // Yellow exit facing East
        add("underground_belt", "default", 0, 6, y + 1, 90); // Yellow entry at (6, y+1) facing East

        // Central Yellow line:
        add("belt", "default", 0, 5, y, 0);
        add("belt", "default", 0, 6, y, 0);
    }

    // STAGE 1: Red + Green -> Yellow (Rows Y = 14 to 25, dy=2 -> 6 rows)
    for (let i = 0; i < 6; ++i) {
        const y = 14 + i * 2;

        // Left Wing Mixer (rot 270, facing West): occupies (1, y) and (1, y+1)
        add("mixer", "default", 0, 1, y, 270);
        // Left output merges Yellow into central bus via underground tunnel:
        // Mixer ejects West to (0, y). Belt turns North, enters underground at (0, y), jumps to (5, y)
        add("belt", "default", 0, 0, y, 270);
        add("belt", "default", 0, 0, y + 1, 0);

        // Right Wing Mixer (rot 90, facing East): occupies (10, y) and (10, y+1)
        add("mixer", "default", 0, 10, y, 90);
        add("belt", "default", 0, 11, y, 90);
        add("belt", "default", 0, 11, y + 1, 0);

        // Red and Green distribution:
        // Red in X=3 and X=8
        // Green in X=5 and X=6
        add("balancer", "splitter-inverse", 0, 3, y, 0); // splits West into (2, y)
        add("belt", "default", 0, 3, y + 1, 0);
        add("balancer", "splitter", 0, 8, y, 0); // splits East into (9, y)
        add("belt", "default", 0, 8, y + 1, 0);

        // Green feeds via underground jumps:
        add("underground_belt", "default", 0, 4, y + 1, 270);
        add("underground_belt", "default", 1, 2, y + 1, 270);
        add("belt", "default", 0, 2, y, 270);

        add("underground_belt", "default", 0, 7, y + 1, 90);
        add("underground_belt", "default", 1, 9, y + 1, 90);
        add("belt", "default", 0, 9, y, 90);

        // Yellow collected up the center (X=5, X=6):
        add("balancer", "merger", 0, 5, y, 0);
        add("belt", "default", 0, 5, y + 1, 0);
        add("balancer", "merger-inverse", 0, 6, y, 0);
        add("belt", "default", 0, 6, y + 1, 0);
    }

    // Top Header: Balancer and Output lines (Y=0, 1)
    add("balancer", "default", 0, 0, 0, 0);
    add("balancer", "default", 0, 10, 0, 0);
    add("belt", "default", 0, 0, 1, 0);
    add("belt", "default", 0, 11, 1, 0);

    // Standardized Input Ports at Bottom (Y=26, 27):
    // X=3: Red In
    add("belt", "default", 0, 3, 26, 0);
    add("belt", "default", 0, 3, 27, 0);
    // X=5, 6: Green In
    add("belt", "default", 0, 5, 26, 0);
    add("belt", "default", 0, 5, 27, 0);
    add("belt", "default", 0, 6, 26, 0);
    add("belt", "default", 0, 6, 27, 0);
    // X=8: Red In (right)
    add("belt", "default", 0, 8, 26, 0);
    add("belt", "default", 0, 8, 27, 0);
    // X=4, 7: Blue In
    add("belt", "default", 0, 4, 26, 0);
    add("belt", "default", 0, 4, 27, 0);
    add("belt", "default", 0, 7, 26, 0);
    add("belt", "default", 0, 7, 27, 0);

    return entities;
}

// -----------------------------------------------------------------------------
// DESIGN 2: THE DIRECT-COUPLED ULTRA-COMPACT 6-TILE MODULE ("Nano-White")
// Width: 6 tiles (X = 0..5)
// Height: 18 tiles (Y = 0..17)
// 8 Stage 1 Mixers (X=2) directly coupled to 8 Stage 2 Mixers (X=4)
//
// X=0: Red input bus
// X=1: Green input bus
// X=2: Stage 1 Mixers (rot 90, facing East): Red + Green -> Yellow
// X=3: Yellow transfer (direct) + Blue underground spine
// X=4: Stage 2 Mixers (rot 90, facing East): Yellow + Blue -> White
// X=5: White output merger bus (moving North)
// -----------------------------------------------------------------------------

function buildDirectCoupledModule() {
    const entities = [];
    function add(b, v, w, x, y, r) {
        entities.push({ b, v, w, x, y, r, o: r });
    }

    const rows = 8;
    for (let i = 0; i < rows; ++i) {
        const y = 1 + i * 2;

        // Stage 1 Mixer: at (2, y), rot 90 (facing East). Occupies (2, y) and (2, y+1)
        add("mixer", "default", 0, 2, y, 90);

        // Stage 2 Mixer: at (4, y), rot 90 (facing East). Occupies (4, y) and (4, y+1)
        add("mixer", "default", 0, 4, y, 90);

        // Red input distribution on X=0:
        add("balancer", "splitter-inverse", 0, 0, y, 0); // splits East to (1, y)
        add("belt", "default", 0, 0, y + 1, 0);

        // Green input distribution on X=1:
        // Red hops over Green via underground:
        add("underground_belt", "default", 0, 0, y, 90); // Red entry at (0, y) facing East
        // Wait, cleaner: Red splitter at (0, y) sends East into underground entry at (1, y)!
        // Green splitter at (1, y+1) sends East into (2, y+1) directly!
        add("belt", "default", 0, 1, y, 90); // Red reaches (2, y)
        add("balancer", "splitter", 0, 1, y + 1, 0); // Green splitter sends East into (2, y+1)

        // Yellow transfer & Blue injection at X=3:
        // Mixer 1 ejects Yellow at (2, y) East -> directly enters (3, y) -> directly enters Mixer 2 at (4, y)!
        add("belt", "default", 0, 3, y, 90); // Yellow transfer link

        // Blue input at (3, y+1):
        // Blue flows down X=3. At (3, y+1), splitter sends Blue East into (4, y+1)!
        // And Blue passes under (3, y) using underground belt:
        // Entry at (3, y+2), exit at (3, y-1) or vice versa!
        add("balancer", "splitter", 0, 3, y + 1, 0); // splits East into (4, y+1)

        // White output on X=5:
        add("balancer", "merger-inverse", 0, 5, y, 0); // collects White from (4, y) going North
        add("belt", "default", 0, 5, y + 1, 0);
    }

    // Input ports at South (Y = 1 + rows*2):
    const portY = 1 + rows * 2;
    add("belt", "default", 0, 0, portY, 0); // Red In
    add("belt", "default", 0, 1, portY, 0); // Green In
    add("belt", "default", 0, 3, portY, 0); // Blue In

    // Output port at North (Y = 0):
    add("belt", "default", 0, 5, 0, 0); // White Out

    return entities;
}

// Generate both
const dualWing = buildDualWingModule();
const bpDualWing = encodeBP(dualWing);

const nano = buildDirectCoupledModule();
const bpNano = encodeBP(nano);

console.log('Dual-Wing Module entities count:', dualWing.length);
console.log('Dual-Wing BP length:', bpDualWing.length);
console.log('Dual-Wing Blueprint:\n', bpDualWing);

console.log('\n----------------------------------------\n');

console.log('Nano-White Module entities count:', nano.length);
console.log('Nano-White BP length:', bpNano.length);
console.log('Nano-White Blueprint:\n', bpNano);

// Save blueprints to file for reference
fs.writeFileSync('C:/Users/mvas2/shapez-portable/shapez-ai/python/data/blueprints_white_dye.json', JSON.stringify({
    dualWing: {
        entitiesCount: dualWing.length,
        width: 12,
        height: 28,
        code: bpDualWing
    },
    nanoWhite: {
        entitiesCount: nano.length,
        width: 6,
        height: 18,
        code: bpNano
    }
}, null, 2));

console.log('\nSaved to blueprints_white_dye.json successfully!');
