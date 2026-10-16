const fs = require('fs');

const bundle = fs.readFileSync('c:/Users/mvas2/shapez-portable/resources/app/bundle.js', 'utf8');

// Find upgrade curves in bundle.js
// Search for upgrades definition
const idx = bundle.indexOf('enumHubGoalRewards');
console.log('Upgrades around enumHubGoalRewards:');
const uIdx = bundle.indexOf('getUpgrades');
if (uIdx !== -1) {
    console.log(bundle.substring(uIdx - 100, uIdx + 800));
}

// Search for base speeds:
// beltBaseSpeed, minerBaseSpeed, processorBaseSpeed
const speeds = bundle.match(/baseSpeed[a-zA-Z]*\s*=\s*[\d.]+/g);
console.log('Base speeds:', speeds);
