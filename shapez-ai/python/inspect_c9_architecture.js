const fs = require('fs');

const entities = JSON.parse(fs.readFileSync('C:/Users/mvas2/shapez-portable/shapez-ai/python/data/entities.json', 'utf8'));

const c9 = entities.filter(e => {
    const o = e.components?.StaticMapEntity?.origin;
    return o && o.x >= 65 && o.x <= 86 && o.y >= 82 && o.y <= 157;
});

console.log('Cluster 9 total entities:', c9.length);

// Analyze X distribution
const xCounts = {};
for (const e of c9) {
    const x = e.components.StaticMapEntity.origin.x;
    xCounts[x] = (xCounts[x] || 0) + 1;
}
console.log('X coordinates in Cluster 9:');
const sortedX = Object.keys(xCounts).map(Number).sort((a,b)=>a-b);
for (const x of sortedX) {
    console.log(`X=${x}: count=${xCounts[x]}`);
}

// Find all mixers (code 15) in Cluster 9
const mixers = c9.filter(e => e.components?.StaticMapEntity?.code === 15);
console.log('\nMixers count in Cluster 9:', mixers.length);

// Group mixers by X
const mixerByX = {};
for (const m of mixers) {
    const o = m.components.StaticMapEntity.origin;
    if (!mixerByX[o.x]) mixerByX[o.x] = [];
    mixerByX[o.x].push(m);
}
for (const x of Object.keys(mixerByX).map(Number).sort((a,b)=>a-b)) {
    console.log(`Mixer column X=${x}: count=${mixerByX[x].length}, Y range=[${Math.min(...mixerByX[x].map(m=>m.components.StaticMapEntity.origin.y))}..${Math.max(...mixerByX[x].map(m=>m.components.StaticMapEntity.origin.y))}]`);
    // Print rotation and sample
    console.log(`  Rotations:`, Array.from(new Set(mixerByX[x].map(m=>m.components.StaticMapEntity.rotation))));
}

// Let's inspect a slice of Y from 120 to 130 to see the repeating unit!
console.log('\n=== Slice Y=120..128 ===');
const slice = c9.filter(e => {
    const y = e.components.StaticMapEntity.origin.y;
    return y >= 120 && y <= 128;
}).sort((a, b) => {
    const ya = a.components.StaticMapEntity.origin.y;
    const yb = b.components.StaticMapEntity.origin.y;
    if (ya !== yb) return ya - yb;
    return a.components.StaticMapEntity.origin.x - b.components.StaticMapEntity.origin.x;
});

for (const e of slice) {
    const o = e.components.StaticMapEntity.origin;
    const rot = e.components.StaticMapEntity.rotation;
    const code = e.components.StaticMapEntity.code;
    const ejector = e.components?.ItemEjector?.slots?.[0]?.item?.data || '';
    console.log(`Y=${o.y}, X=${o.x}: code=${code}, rot=${rot}, ejector=${ejector}`);
}
