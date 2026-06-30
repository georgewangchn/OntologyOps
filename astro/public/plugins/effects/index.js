import { preloadImages } from './utils.js';
import { ImageTrail } from './imageTrail.js';

document.addEventListener('DOMContentLoaded', () => {
    // Preload all images
    preloadImages('.effects__img-inner').then(() => {
        new ImageTrail(document.querySelector('.effects'));
    });

});
