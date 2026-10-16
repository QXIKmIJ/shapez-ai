const fs = require('fs');

// Let's inspect how Shapez rotates slot positions and directions
const bundle = fs.readFileSync('c:/Users/mvas2/shapez-portable/resources/app/bundle.js', 'utf8');

// Find rotateDirection and slot rotation
const idx = bundle.indexOf('function rotateDirection(');
if (idx !== -1) {
    console.log(bundle.substring(idx, idx + 400));
} else {
    // Find enumDirection
    const dIdx = bundle.indexOf('enumDirection');
    console.log(bundle.substring(dIdx, dIdx + 400));
}
