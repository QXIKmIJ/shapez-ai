const fs = require('fs');

const bundle = fs.readFileSync('c:/Users/mvas2/shapez-portable/resources/app/bundle.js', 'utf8');

// Load blueprints
const bps = JSON.parse(fs.readFileSync('C:/Users/mvas2/shapez-portable/shapez-ai/python/data/blueprints_white_dye.json', 'utf8'));

// Test decompression and entity validation
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

function decompressX64(e) {
    return null == e ? '' : '' == e ? null : _decompress((e = e.replace(/ /g, '+')).length, 32, function (t) {
        if (!a_x64[o_x64]) { a_x64[o_x64] = {}; for (var r = 0; r < o_x64.length; r++) a_x64[o_x64][o_x64.charAt(r)] = r; }
        return a_x64[o_x64][e.charAt(t)];
    });
}

for (const [name, data] of Object.entries(bps)) {
    const raw = data.code.replace('[SHAPEZ-BP1:', '').replace(']', '');
    const json = decompressX64(raw);
    const parsed = JSON.parse(json);
    console.log(`Blueprint ${name}:`);
    console.log(`  Version: ${parsed.f}, Layer: ${parsed.l}`);
    console.log(`  Entities count: ${parsed.e.length}`);
    const bldCounts = {};
    for (const ent of parsed.e) {
        const k = `${ent.b}:${ent.v}:w${ent.w}`;
        bldCounts[k] = (bldCounts[k] || 0) + 1;
    }
    console.log('  Breakdown:', bldCounts);
}
