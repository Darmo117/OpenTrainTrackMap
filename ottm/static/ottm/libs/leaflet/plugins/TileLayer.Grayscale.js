/*
 * L.TileLayer.Grayscale is a regular tilelayer with grayscale makeover.
 */

import * as L from "../leaflet-src.esm.js";

L.TileLayer.Grayscale = L.TileLayer.extend({
  options: {
    quotaRed: 21,
    quotaGreen: 71,
    quotaBlue: 8,
    quotaDividerTune: 0,
    quotaDivider: function () {
      return this.quotaRed + this.quotaGreen + this.quotaBlue + this.quotaDividerTune;
    }
  },

  initialize: function (url, options) {
    options = options ?? {}
    options.crossOrigin = true;
    L.TileLayer.prototype.initialize.call(this, url, options);

    this.on("tileload", function (e) {
      this._makeGrayscale(e.tile);
    });
  },

  _createTile: function () {
    const tile = L.TileLayer.prototype._createTile.call(this);
    tile.crossOrigin = "Anonymous";
    return tile;
  },

  _makeGrayscale: function (img) {
    if (img.getAttribute("data-grayscaled")) {
      return;
    }

    img.crossOrigin = "";
    const canvas = document.createElement("canvas");
    canvas.width = img.width;
    canvas.height = img.height;
    const context = canvas.getContext("2d");
    context.drawImage(img, 0, 0);

    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    const pixels = imageData.data;
    for (let i = 0, n = pixels.length; i < n; i += 4) {
      pixels[i] = pixels[i + 1] = pixels[i + 2] =
        (this.options.quotaRed * pixels[i] + this.options.quotaGreen * pixels[i + 1] + this.options.quotaBlue * pixels[i + 2])
        / this.options.quotaDivider();
    }
    context.putImageData(imageData, 0, 0);
    img.setAttribute("data-grayscaled", true);
    img.src = canvas.toDataURL();
  }
});

L.tileLayer.grayscale = function (url, options) {
  return new L.TileLayer.Grayscale(url, options);
};
