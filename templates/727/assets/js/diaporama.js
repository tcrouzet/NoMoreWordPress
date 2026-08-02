document.addEventListener('DOMContentLoaded', async () => {
  const slideshow = document.querySelector('.geo-slideshow[data-slideshow]');
  if (!slideshow || typeof L === 'undefined') return;

  const slide = slideshow.querySelector('.slideshow-slide');
  const photoDate = slideshow.querySelector('.slideshow-date');
  const caption = slideshow.querySelector('.slideshow-caption');
  const mapShell = slideshow.querySelector('.slideshow-map-shell');
  const mapContainer = slideshow.querySelector('.slideshow-map');
  const mapOpen = slideshow.querySelector('.slideshow-map-open');

  try {
    const kind = encodeURIComponent(slideshow.dataset.slideshow);
    const version = encodeURIComponent(slideshow.dataset.version);
    const response = await fetch(`/static/diaporama-${kind}.json?ver=${version}`);
    if (!response.ok) throw new Error(response.statusText);
    const data = await response.json();
    const points = data.points || [];
    if (!points.length) {
      caption.textContent = 'Aucune photo géolocalisée.';
      return;
    }

    const map = L.map(mapContainer, {
      preferCanvas: true,
      scrollWheelZoom: false
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: ''
    }).addTo(map);

    let current = 0;
    let mapExpanded = false;
    let markers = [];
    const allBounds = L.latLngBounds(points.map(point => [point.lat, point.lon]));

    function toggleMap(expanded = !mapExpanded) {
      mapExpanded = expanded;
      mapShell.classList.toggle('expanded', mapExpanded);
      slideshow.classList.toggle('map-expanded', mapExpanded);
      window.requestAnimationFrame(() => {
        map.invalidateSize();
        if (mapExpanded) {
          map.fitBounds(allBounds, { padding: [16, 16] });
        } else {
          const point = points[current];
          map.setView([point.lat, point.lon], 10);
        }
      });
    }

    function show(index, moveMap = true) {
      current = (index + points.length) % points.length;
      const point = points[current];
      slide.style.backgroundImage = `url("${point.image}")`;
      slide.setAttribute('aria-label', point.alt || `Photo ${current + 1}`);
      const dateParts = String(point.date || '').slice(0, 10).split('-').map(Number);
      if (dateParts.length === 3 && dateParts.every(Number.isFinite)) {
        const date = new Date(dateParts[0], dateParts[1] - 1, dateParts[2]);
        photoDate.dateTime = String(point.date).slice(0, 10);
        photoDate.textContent = new Intl.DateTimeFormat('fr-FR', {
          day: 'numeric',
          month: 'long',
          year: 'numeric'
        }).format(date);
        photoDate.hidden = false;
      } else {
        photoDate.removeAttribute('datetime');
        photoDate.textContent = '';
        photoDate.hidden = true;
      }
      caption.textContent = `${point.alt ? `${point.alt} — ` : ''}${current + 1}/${points.length}`;
      markers.forEach((marker, markerIndex) => marker.setStyle({
        radius: markerIndex === current ? 9 : 5,
        weight: markerIndex === current ? 3 : 1,
        color: markerIndex === current ? '#fffdf7' : '#171714',
        fillColor: markerIndex === current ? '#db4b2f' : '#3458b0',
        fillOpacity: 1
      }));
      markers[current].bringToFront();
      if (moveMap && !mapExpanded) map.setView([point.lat, point.lon], 10);
    }

    markers = points.map((point, index) => {
      const marker = L.circleMarker([point.lat, point.lon], {
        radius: 5,
        weight: 1,
        color: '#171714',
        fillColor: '#3458b0',
        fillOpacity: 1,
        bubblingMouseEvents: false
      }).addTo(map);
      marker.on('click', () => {
        if (mapExpanded) toggleMap(false);
        show(index);
      });
      return marker;
    });

    map.setView([points[0].lat, points[0].lon], 10);
    mapOpen.addEventListener('click', () => toggleMap(true));
    slideshow.querySelector('[data-slide-previous]').addEventListener('click', () => {
      if (mapExpanded) toggleMap(false);
      show(current - 1);
    });
    slideshow.querySelector('[data-slide-next]').addEventListener('click', () => {
      if (mapExpanded) toggleMap(false);
      show(current + 1);
    });
    slideshow.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft') show(current - 1);
      if (event.key === 'ArrowRight') show(current + 1);
      if (event.key === 'Escape' && mapExpanded) toggleMap(false);
    });
    slideshow.tabIndex = 0;
    show(0, false);
  } catch (error) {
    caption.textContent = 'Le diaporama est indisponible.';
  }
});
