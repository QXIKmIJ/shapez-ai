const fs = require('fs');
const bundle = fs.readFileSync('c:/Users/mvas2/shapez-portable/resources/app/bundle.js', 'utf8');

const regex = /registerBuildingVariant\s*\(\s*(\d+|['"][^'"]+['"])\s*,\s*([^,]+)(?:,\s*([^,)]+))?(?:,\s*([^,)]+))?\s*\)/g;
let m;
while ((m = regex.exec(bundle)) !== null) {
    console.log(`Code ${m[1]}: class=${m[2].trim()}, variant=${m[3]?.trim()}, rotVariant=${m[4]?.trim()}`);
}
