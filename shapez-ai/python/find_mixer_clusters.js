const fs = require('fs');

const entities = JSON.parse(fs.readFileSync('C:/Users/mvas2/shapez-portable/shapez-ai/python/data/entities.json', 'utf8'));

// Find all code 15 and 61
const code15 = entities.filter(e => e.components?.StaticMapEntity?.code === 15);
const code61 = entities.filter(e => e.components?.StaticMapEntity?.code === 61);

console.log('Code 15 entities (Mixer):', code15.length);
console.log('Code 61 entities (Mirrored):', code61.length);

// Let's inspect some samples of code 15 and 61
if (code15.length > 0) {
    console.log('Sample code 15:', JSON.stringify(code15[0]));
}
if (code61.length > 0) {
    console.log('Sample code 61:', JSON.stringify(code61[0]));
}

// Cluster code 15 + code 61 entities
const allMixers = [...code15, ...code61];
const clusters = [];

for (const m of allMixers) {
    const o = m.components.StaticMapEntity.origin;
    let added = false;
    for (const c of clusters) {
        if (Math.abs(o.x - c.centerX) < 35 && Math.abs(o.y - c.centerY) < 35) {
            c.members.push(m);
            c.minX = Math.min(c.minX, o.x);
            c.maxX = Math.max(c.maxX, o.x);
            c.minY = Math.min(c.minY, o.y);
            c.maxY = Math.max(c.maxY, o.y);
            c.centerX = (c.minX + c.maxX) / 2;
            c.centerY = (c.minY + c.maxY) / 2;
            added = true;
            break;
        }
    }
    if (!added) {
        clusters.push({
            centerX: o.x,
            centerY: o.y,
            minX: o.x,
            maxX: o.x,
            minY: o.y,
            maxY: o.y,
            members: [m]
        });
    }
}

// Merge overlapping clusters
let merged = true;
while (merged) {
    merged = false;
    for (let i = 0; i < clusters.length; ++i) {
        for (let j = i + 1; j < clusters.length; ++j) {
            const c1 = clusters[i];
            const c2 = clusters[j];
            if (Math.abs(c1.centerX - c2.centerX) < 40 && Math.abs(c1.centerY - c2.centerY) < 40) {
                c1.members.push(...c2.members);
                c1.minX = Math.min(c1.minX, c2.minX);
                c1.maxX = Math.max(c1.maxX, c2.maxX);
                c1.minY = Math.min(c1.minY, c2.minY);
                c1.maxY = Math.max(c1.maxY, c2.maxY);
                c1.centerX = (c1.minX + c1.maxX) / 2;
                c1.centerY = (c1.minY + c1.maxY) / 2;
                clusters.splice(j, 1);
                merged = true;
                break;
            }
        }
        if (merged) break;
    }
}

console.log('\nFound clusters of mixers/mirrored:', clusters.length);
clusters.sort((a, b) => b.members.length - a.members.length);
for (let i = 0; i < clusters.length; ++i) {
    const c = clusters[i];
    console.log(`Cluster ${i + 1}: ${c.members.length} machines at [${c.minX}..${c.maxX}, ${c.minY}..${c.maxY}], size=(${c.maxX - c.minX + 1} x ${c.maxY - c.minY + 1})`);
}
