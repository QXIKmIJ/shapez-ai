const fs = require('fs');
const path = require('path');

// We have the compressX64 implementation from bundle.js
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

// Test compress and decompress
const testPayload = {
    f: 1,
    l: "regular",
    e: [
        { b: "belt", v: "default", w: 0, x: 0, y: 0, r: 0, o: 0 },
        { b: "mixer", v: "default", w: 0, x: 1, y: 0, r: 0, o: 0 }
    ]
};

const json = JSON.stringify(testPayload);
const comp = compressX64(json);
const bpString = "[SHAPEZ-BP1:" + comp + "]";
console.log('Sample Blueprint String:', bpString);

const decomp = decompressX64(comp);
console.log('Decompressed equals original:', decomp === json);
