/**
 * Hooks the editor to the given map.
 *
 * @param map A Leaflet map object.
 */
function initEditor(map) {
  const EditControl = L.Control.extend({
    options: {
      position: "topleft",
    },

    onAdd: function (map) {
      const container = L.DomUtil.create("div", "leaflet-control leaflet-bar");
      const link = L.DomUtil.create("a", "", container);

      link.href = "#";
      link.title = ottm.translations.get(`map.controls.edit.${this.options.kind}.tooltip`);
      link.innerHTML = this.options.html;
      L.DomEvent.on(link, "click", L.DomEvent.stop)
        .on(link, "click", () => {
          window.LAYER = this.options.callback.call(map.editTools);
        }, this);

      return container;
    },
  });

  const NewMarkerControl = EditControl.extend({
    options: {
      callback: map.editTools.startMarker,
      kind: "new_marker",
      html: '<span class="mdi mdi-vector-point"></span>',
    }
  });

  const NewLineControl = EditControl.extend({
    options: {
      callback: map.editTools.startPolyline,
      kind: "new_line",
      html: '<span class="mdi mdi-vector-polyline"></span>',
    }
  });

  const NewPolygonControl = EditControl.extend({
    options: {
      callback: map.editTools.startPolygon,
      kind: "new_polygon",
      html: '<span class="mdi mdi-vector-polygon"></span>',
    }
  });

  map.addControl(new NewMarkerControl());
  map.addControl(new NewLineControl());
  map.addControl(new NewPolygonControl());

  let snapHandler = new L.Handler.MarkerSnap(map, null, {
    snapDistance: 10,
  });
  let snapMarker = L.marker(map.getCenter(), {
    icon: map.editTools.createVertexIcon({className: "leaflet-div-icon leaflet-drawing-icon"}),
    opacity: 1,
    zIndexOffset: 1000
  });
  snapHandler.watchMarker(snapMarker);

  function addSnapGuide(g) {
    snapHandler.addGuideLayer(g);
  }

  function removeSnapGuide(g) {
    // No clean way to remove a guide from the list
    snapHandler._guides.splice(snapHandler._guides.indexOf(g), 1);
  }

  function followMouse(e) {
    snapMarker.setLatLng(e.latlng);
  }

  // We have to remove the currently dragged layer from the guides list
  // as otherwise geometryutils would throw errors.
  // The object is added back into the list after the drag has stopped.
  // TODO "merge" points on snap
  map.on("editable:created", function (e) {
    const layer = e.layer;
    addSnapGuide(layer);
    if (layer instanceof L.Marker) {
      // Markers do not fire "editable:vertex:*" events on their own
      layer.on("dragstart", function () {
        map.fire("editable:vertex:dragstart", {layer: layer, vertex: layer});
      });
      layer.on("dragend", function () {
        map.fire("editable:vertex:dragend", {layer: layer, vertex: layer});
      });
      layer.on("click", function () {
        map.fire("editable:vertex:rawclick", {layer: layer, vertex: layer});
      })
    }
  });
  map.on("editable:vertex:dragstart", function (e) {
    removeSnapGuide(e.layer);
    snapHandler.watchMarker(e.vertex);
  });
  map.on("editable:vertex:dragend", function (e) {
    addSnapGuide(e.layer);
    snapHandler.unwatchMarker(e.vertex);
  });
  map.on("editable:drawing:start", function (e) {
    removeSnapGuide(e.layer);
    this.on("mousemove", followMouse);
  });
  map.on("editable:drawing:end", function (e) {
    addSnapGuide(e.layer);
    this.off("mousemove", followMouse);
    snapMarker.remove();
  });
  map.on("editable:drawing:click", function (e) {
    // Leaflet copy event data to another object when firing,
    // so the event object we have here is not the one fired by
    // Leaflet.Editable; it's not a deep copy though, so we can change
    // the other objects that have a reference here.
    let latlng = snapMarker.getLatLng();
    e.latlng.lat = latlng.lat;
    e.latlng.lng = latlng.lng;
  });
  snapMarker.on("snap", function () {
    snapMarker.addTo(map);
  });
  snapMarker.on("unsnap", function () {
    snapMarker.remove();
  });
  // Continue editing on Ctrl+LMB on first or last vertex of polyline
  map.on("editable:vertex:ctrlclick editable:vertex:metakeyclick", function (e) { // TODO put in context menu
    e.vertex.continue();
  });
  map.on("editable:vertex:rawclick", function (e) {
    if (!(e.layer instanceof L.Marker)) {
      e.cancel(); // Disable default behavior: delete vertex
    }
    const icon = e.vertex._icon;
    console.log(icon); // DEBUG
    // TODO select vertex
  });
  // TODO polyline/polygon selection
}
