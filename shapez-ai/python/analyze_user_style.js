const fs = require('fs');
const path = require('path');

const entities = JSON.parse(fs.readFileSync('C:/Users/mvas2/shapez-portable/shapez-ai/python/data/entities.json', 'utf8'));

console.log('Total entities:', entities.length);

// Analyze building types
const typeCounts = {};
for (const e of entities) {
    const code = e.components?.StaticMapEntity?.code;
    typeCounts[code] = (typeCounts[code] || 0) + 1;
}

console.log('Building code counts (top 30):');
const sortedCodes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]);
console.log(sortedCodes.slice(0, 30));

// Let's find mixers
// In shapez bundle: 15 is color mixer (and maybe other codes)
// Let's search bundle.js for all meta building definitions and their codes
const bundle = fs.readFileSync('c:/Users/mvas2/shapez-portable/resources/app/bundle.js', 'utf8');

// Let's write a small helper to map codes to building IDs
// In bundle.js, gBuildingVariants maps code to { metaInstance, variant, rotationVariant }
// Let's find the table or definitions in bundle.js
const codeToBuilding = {};
// Let's inspect where mixer entities are located in the world
const mixerEntities = [];
for (const e of entities) {
    const sme = e.components?.StaticMapEntity;
    if (!sme) continue;
    // Mixers usually have ColorMixer component or code 15
    if (e.components?.ColorMixer || sme.code === 15 || sme.code === 61 || (sme.code >= 15 && sme.code <= 19)) {
        mixerEntities.push(e);
    }
}
console.log('Entities with mixer-like components/codes:', mixerEntities.length);

// Let's inspect component names across all entities
const compNames = new Set();
for (const e of entities) {
    for (const k of Object.keys(e.components || {})) {
        compNames.add(k);
    }
}
console.log('All component names in world:', Array.from(compNames));

// Find entities with ColorMixer component
const trueMixers = entities.filter(e => e.components?.ColorMixer);
console.log('Entities with actual ColorMixer component:', trueMixers.length);

// Find entities with Painter component
const painters = entities.filter(e => e.components?.Painter);
console.log('Entities with Painter component:', painters.length);

// Find entities with ItemProcessor (cutters, stackers, rotaters)
const itemProcessors = entities.filter(e => e.components?.ItemProcessor);
console.log('Entities with ItemProcessor component:', itemProcessors.length);

// Cluster trueMixers by coordinates to find all color factory locations!
const clusters = [];
for (const m of trueMixers) {
    const o = m.components.StaticMapEntity.origin;
    let found = false;
    for (const c of clusters) {
        if (Math.abs(o.x - c.centerX) < 30 && Math.abs(o.y - c.centerY) < 30) {
            c.members.push(m);
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

console.log('Color Mixer Clusters found:', clusters.length);
for (let i = 0; i < clusters.length; ++i) {
    const c = clusters[i];
    console.log(`Cluster ${i + 1}: count=${c.members.length}, bbox=[${c.minX}..${c.maxX}, ${c.minY}..${c.maxY}]`);
}
