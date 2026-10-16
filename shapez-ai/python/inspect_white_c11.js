const fs = require('fs');

const entities = JSON.parse(fs.readFileSync('C:/Users/mvas2/shapez-portable/shapez-ai/python/data/entities.json', 'utf8'));

// Filter all entities in White Cluster 11: [68..83, 74..115]
const c11 = entities.filter(e => {
    const o = e.components?.StaticMapEntity?.origin;
    return o && o.x >= 68 && o.x <= 83 && o.y >= 74 && o.y <= 115;
});

console.log('Cluster 11 entities count:', c11.length);

// Let's print out what types of buildings and where
const byY = {};
for (const e of c11) {
    const o = e.components.StaticMapEntity.origin;
    if (!byY[o.y]) byY[o.y] = [];
    byY[o.y].push(e);
}

// Print row by row
const sortedY = Object.keys(byY).map(Number).sort((a,b)=>a-b);
for (const y of sortedY) {
    const row = byY[y].sort((a,b)=>a.components.StaticMapEntity.origin.x - b.components.StaticMapEntity.origin.x);
    const rowDesc = row.map(e => {
        const o = e.components.StaticMapEntity.origin;
        const code = e.components.StaticMapEntity.code;
        const rot = e.components.StaticMapEntity.rotation;
        const color = e.components?.ItemEjector?.slots?.[0]?.item?.data || '';
        return `x${o.x}:[${code}|r${rot}${color ? '|' + color : ''}]`;
    }).join(' ');
    console.log(`Y=${y.toString().padStart(3, ' ')}: ${rowDesc}`);
}
