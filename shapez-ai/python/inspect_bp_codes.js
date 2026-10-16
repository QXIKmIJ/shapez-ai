const fs = require('fs');

const bundle = fs.readFileSync('c:/Users/mvas2/shapez-portable/resources/app/bundle.js', 'utf8');

// In bundle.js, let's find getBuildingDataFromCode implementation or lookup
// Let's create an environment to run getBuildingDataFromCode
// Or inspect gBuildingVariants
const idx = bundle.indexOf('gBuildingVariants[');
console.log('Sample gBuildingVariants:');
let pos = 0;
const codes = [1, 2, 3, 5, 6, 15, 22, 23, 47, 48];
for (const c of codes) {
    const p = bundle.indexOf(`registerBuildingVariant(${c},`);
    if (p !== -1) {
        console.log(`Code ${c}:`, bundle.substring(p, p + 80));
    }
}
