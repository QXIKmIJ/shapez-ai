const fs = require('fs');
const entities = JSON.parse(fs.readFileSync('C:/Users/mvas2/shapez-portable/shapez-ai/python/data/entities.json', 'utf8'));

const whiteEjectors = entities.filter(e => {
    const slots = e.components?.ItemEjector?.slots;
    return slots && slots.some(s => s.item?.$ === 'color' && s.item?.data === 'white');
});

console.log('Entities ejecting white color:', whiteEjectors.length);

const whiteClusters = [];
for (const e of whiteEjectors) {
    const o = e.components.StaticMapEntity.origin;
    let found = false;
    for (const c of whiteClusters) {
        if (Math.abs(o.x - c.centerX) < 30 && Math.abs(o.y - c.centerY) < 30) {
            c.members.push(e);
            c.minX = Math.min(c.minX, o.x);
            c.maxX = Math.max(c.maxX, o.x);
            c.minY = Math.min(c.minY, o.y);
            c.maxY = Math.max(c.maxY, o.y);
            c.centerX = (c.minX + c.maxX) / 2;
            c.centerY = (c.minY + c.maxY) / 2;
            found = true;
            break;
        }
    }
    if (!found) {
        whiteClusters.push({
            centerX: o.x,
            centerY: o.y,
            minX: o.x,
            maxX: o.x,
            minY: o.y,
            maxY: o.y,
            members: [e]
        });
    }
}

for (let i = 0; i < whiteClusters.length; ++i) {
    const c = whiteClusters[i];
    console.log(`White Cluster ${i+1}: count=${c.members.length}, bbox=[${c.minX}..${c.maxX}, ${c.minY}..${c.maxY}]`);
    // Check building codes of ejectors
    const codes = {};
    for (const m of c.members) {
        const code = m.components.StaticMapEntity.code;
        codes[code] = (codes[code] || 0) + 1;
    }
    console.log('  Codes:', codes);
}
