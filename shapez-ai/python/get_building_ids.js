const fs = require('fs');
const bundle = fs.readFileSync('c:/Users/mvas2/shapez-portable/resources/app/bundle.js', 'utf8');

// Find all matches of getId
const regex = /getId\(\)\s*\{\s*return\s*['"]([a-zA-Z0-9_\-]+)['"]\s*\}/g;
let m;
const ids = new Set();
while ((m = regex.exec(bundle)) !== null) {
    ids.add(m[1]);
}
console.log('Building IDs from getId():', Array.from(ids));

// Also let's check code 22 and 23
// Where does code 22 come from?
// In Shapez, codes are assigned sequentially or in an enum!
// Let's find where registerBuildingVariant is called in bundle.js
const regMatches = bundle.match(/registerBuildingVariant\([^)]+\)/g);
console.log('Sample registerBuildingVariant calls (first 20):');
if (regMatches) {
    console.log(regMatches.slice(0, 20));
}
