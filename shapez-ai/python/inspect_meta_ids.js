const fs = require('fs');
const bundle = fs.readFileSync('c:/Users/mvas2/shapez-portable/resources/app/bundle.js', 'utf8');

// Find all getId definitions for Meta buildings
const regex = /Meta(\w+)Building[^{]*\{[^{]*getId\(\)\s*\{\s*return\s*['"]([^'"]+)['"]/g;
let m;
while ((m = regex.exec(bundle)) !== null) {
    console.log(`Meta${m[1]}Building -> id: "${m[2]}"`);
}

// Check variants for MetaBalancerBuilding
const bIdx = bundle.indexOf('MetaBalancerBuilding');
console.log(bundle.substring(bIdx, bIdx + 1500));
