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

  // map.pm.addControls({
  //   position: 'topleft',
  //   drawCircleMarker: false,
  //   drawCircle: false,
  //   drawText: false,
  //   drawRectangle: false,
  //   cutPolygon: false,
  //   editMode: false,
  //   dragMode: false,
  //   rotateMode: false,
  // });
  // map.pm.enableGlobalEditMode();
  let snap = new L.Handler.MarkerSnap(map);
  let snapMarker = L.marker(map.getCenter(), {
    icon: map.editTools.createVertexIcon({className: 'leaflet-div-icon leaflet-drawing-icon'}),
    opacity: 1,
    zIndexOffset: 1000
  });
  snap.watchMarker(snapMarker);

  function addSnapGuide(g) {
    snap.addGuideLayer(g);
  }

  function removeSnapGuide(g) {
    // No clean way to remove a guide from the list
    snap._guides.splice(snap._guides.indexOf(g), 1);
  }

  function followMouse(e) {
    snapMarker.setLatLng(e.latlng);
  }

  // We have to remove the currently dragged layer from the guides list
  // as otherwise geometryutils would throw errors.
  // The object is added back into the list after the drag has stopped.
  // TODO merge points on snap
  map.on("editable:created", function (e) {
    addSnapGuide(e.layer);
  });
  map.on("editable:vertex:dragstart", function (e) {
    removeSnapGuide(e.layer);
    snap.watchMarker(e.vertex);
  });
  map.on("editable:vertex:dragend", function (e) {
    addSnapGuide(e.layer);
    snap.unwatchMarker(e.vertex);
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
  map.on("editable:vertex:ctrlclick editable:vertex:metakeyclick", function (e) {
    e.vertex.continue();
  });
  // map.on("editable:vertex:clicked", function (e) {
  //   e.vertex.set;
  // });
}
