const fs = require('fs');
const path = require('path');

const ch = String.fromCharCode;
const a_x64 = {};
const o_x64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-$';

function _decompress(e, t, r) {
    var n, o, a, s, l, c, u, h = [], d = 4, g = 4, A = 3, p = '', f = [], m = { val: r(0), position: t, index: 1 };
    for (n = 0; n < 3; n += 1) h[n] = n;
    for (a = 0, l = Math.pow(2, 2), c = 1; c != l;) s = m.val & m.position, m.position >>= 1, 0 == m.position && (m.position = t, m.val = r(m.index++)), a |= (s > 0 ? 1 : 0) * c, c <<= 1;
    switch (a) {
        case 0: for (a = 0, l = Math.pow(2, 8), c = 1; c != l;) s = m.val & m.position, m.position >>= 1, 0 == m.position && (m.position = t, m.val = r(m.index++)), a |= (s > 0 ? 1 : 0) * c, c <<= 1; u = ch(a); break;
        case 1: for (a = 0, l = Math.pow(2, 16), c = 1; c != l;) s = m.val & m.position, m.position >>= 1, 0 == m.position && (m.position = t, m.val = r(m.index++)), a |= (s > 0 ? 1 : 0) * c, c <<= 1; u = ch(a); break;
        case 2: return '';
    }
    for (h[3] = u, o = u, f.push(u); ;) {
        if (m.index > e) return '';
        for (a = 0, l = Math.pow(2, A), c = 1; c != l;) s = m.val & m.position, m.position >>= 1, 0 == m.position && (m.position = t, m.val = r(m.index++)), a |= (s > 0 ? 1 : 0) * c, c <<= 1;
        switch (u = a) {
            case 0: for (a = 0, l = Math.pow(2, 8), c = 1; c != l;) s = m.val & m.position, m.position >>= 1, 0 == m.position && (m.position = t, m.val = r(m.index++)), a |= (s > 0 ? 1 : 0) * c, c <<= 1; h[g++] = ch(a), u = g - 1, d--; break;
            case 1: for (a = 0, l = Math.pow(2, 16), c = 1; c != l;) s = m.val & m.position, m.position >>= 1, 0 == m.position && (m.position = t, m.val = r(m.index++)), a |= (s > 0 ? 1 : 0) * c, c <<= 1; h[g++] = ch(a), u = g - 1, d--; break;
            case 2: return f.join('');
        }
        if (0 == d && (d = Math.pow(2, A), A++), h[u]) p = h[u]; else { if (u !== g) return null; p = o + o.charAt(0); }
        f.push(p), h[g++] = o + p.charAt(0), o = p, 0 == --d && (d = Math.pow(2, A), A++);
    }
}

function getBaseValue(e, t) {
    if (!a_x64[e]) { a_x64[e] = {}; for (var r = 0; r < e.length; r++) a_x64[e][e.charAt(r)] = r; }
    return a_x64[e][t];
}

function decompressX64(e) {
    return null == e ? '' : '' == e ? null : _decompress((e = e.replace(/ /g, '+')).length, 32, function (t) {
        return getBaseValue(o_x64, e.charAt(t));
    });
}

const intAlphabet = "!#%&'()*+,-./:;<=>?@[]^_`{|}~\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xffABCDEFGHIJKLMNOPQRSTUVWXYZ";
const decompressIntCache = {};
function decompressInt(e) {
    if (decompressIntCache[e]) return decompressIntCache[e];
    for (var t = 0, r = (e = '' + e).length - 1; r >= 0; --r) t = t * intAlphabet.length + intAlphabet.indexOf(e.charAt(r));
    return t -= 1, decompressIntCache[e] = t;
}

function decompressObject(e) {
    if (e.keys && e.values && e.data) {
        var t = e.keys, r = e.values;
        function decompressObjectInternal(e, t, r) {
            if (Array.isArray(e)) {
                var arr = [];
                for (var i = 0; i < e.length; ++i) arr.push(decompressObjectInternal(e[i], t, r));
                return arr;
            }
            if (typeof e === 'object' && null !== e) {
                var obj = {};
                for (var a in e) {
                    var s = decompressInt(a);
                    var l = e[a];
                    obj[t[s]] = decompressObjectInternal(l, t, r);
                }
                return obj;
            }
            return typeof e === 'string' ? r[decompressInt(e)] : e;
        }
        return decompressObjectInternal(e.data, t, r);
    }
    return e;
}

const savePath = path.join(process.env.APPDATA, 'shapez.io', 'saves', 'savegame-f64bc08e8db4e59cd543fabbfee55d2b775450d9.bin');
console.log('Reading savegame from:', savePath);
const str = fs.readFileSync(savePath, 'utf8');
const payload = str.substr(1);
console.log('Decompressing payload of length:', payload.length);
const uncompressed = decompressX64(payload);
console.log('Uncompressed length:', uncompressed ? uncompressed.length : 0);
const rawJson = uncompressed.substr(40);
const rawObj = JSON.parse(rawJson);
const fullSave = decompressObject(rawObj);

console.log('Save version:', fullSave.version);
console.log('Stats:', fullSave.stats);
console.log('Entities in dump:', fullSave.dump.entities ? fullSave.dump.entities.length : 0);
console.log('Hub goals:', fullSave.dump.hubGoals ? {
    level: fullSave.dump.hubGoals.level,
    currentGoal: fullSave.dump.hubGoals.currentGoal,
    upgradeLevels: fullSave.dump.hubGoals.upgradeLevels,
    upgradeImprovements: fullSave.dump.hubGoals.upgradeImprovements
} : 'none');

const outDir = path.join(__dirname, 'data');
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

fs.writeFileSync(path.join(outDir, 'decompressed_save_meta.json'), JSON.stringify({
    version: fullSave.version,
    stats: fullSave.stats,
    hubGoals: fullSave.dump.hubGoals,
    entityCount: fullSave.dump.entities.length
}, null, 2));

fs.writeFileSync(path.join(outDir, 'entities.json'), JSON.stringify(fullSave.dump.entities));
console.log('Dumped entities.json successfully!');
