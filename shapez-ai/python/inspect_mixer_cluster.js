const fs = require('fs');

const entities = JSON.parse(fs.readFileSync('C:/Users/mvas2/shapez-portable/shapez-ai/python/data/entities.json', 'utf8'));

// Find what items are ejected in each cluster
const clusters = [
    { name: "Cluster 1", bbox: [-141, -18, -101, 17] },
    { name: "Cluster 2", bbox: [63, -18, 110, 17] },
    { name: "Cluster 3", bbox: [-23, -18, 29, 39] },
    { name: "Cluster 4", bbox: [-91, -18, -40, 17] },
    { name: "Cluster 5", bbox: [-18, 56, 17, 100] },
    { name: "Cluster 6", bbox: [-18, 110, 17, 140] },
    { name: "Cluster 7", bbox: [200, 146, 265, 185] },
    { name: "Cluster 8", bbox: [-23, -57, 31, -13] },
    { name: "Cluster 9", bbox: [65, 82, 86, 157] },
    { name: "Cluster 10", bbox: [116, 82, 137, 153] },
    { name: "Cluster 15", bbox: [-1, -144, 50, -124] },
    { name: "Cluster 16", bbox: [419, -1006, 481, -1001] },
];

for (const c of clusters) {
    const inBox = entities.filter(e => {
        const o = e.components?.StaticMapEntity?.origin;
        return o && o.x >= c.bbox[0] - 2 && o.x <= c.bbox[2] + 2 && o.y >= c.bbox[1] - 2 && o.y <= c.bbox[3] + 2;
    });

    const ejectedColors = new Set();
    const ejectedShapes = new Set();
    const codeCounts = {};

    for (const e of inBox) {
        const code = e.components?.StaticMapEntity?.code;
        codeCounts[code] = (codeCounts[code] || 0) + 1;

        const ejector = e.components?.ItemEjector;
        if (ejector?.slots) {
            for (const s of ejector.slots) {
                if (s.item) {
                    if (s.item.$ === 'color') ejectedColors.add(s.item.data);
                    if (s.item.$ === 'shape') ejectedShapes.add(s.item.data);
                }
            }
        }
    }

    console.log(`\n=== ${c.name} [${c.bbox[0]}..${c.bbox[2]}, ${c.bbox[1]}..${c.bbox[3]}] ===`);
    console.log(`Total entities: ${inBox.length}`);
    console.log(`Colors produced: ${Array.from(ejectedColors).join(', ') || 'none observed'}`);
    if (ejectedShapes.size > 0) {
        console.log(`Shapes produced: ${Array.from(ejectedShapes).slice(0, 3).join(', ')}`);
    }
    console.log(`Top building codes:`, Object.entries(codeCounts).sort((a,b)=>b[1]-a[1]).slice(0, 10));
}
