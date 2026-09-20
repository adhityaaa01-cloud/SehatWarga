/** Leaflet / OpenStreetMap. Device coordinates stay in this page's memory. */
function calculateDistanceKm(lat1,lon1,lat2,lon2) {
  const rad=n=>n*Math.PI/180;
  const a=Math.sin(rad(lat2-lat1)/2)**2+Math.cos(rad(lat1))*Math.cos(rad(lat2))*Math.sin(rad(lon2-lon1)/2)**2;
  return (6371*2*Math.atan2(Math.sqrt(a),Math.sqrt(Math.max(0,1-a)))).toFixed(1);
}
function facilityNode(tag,text,cls) {const node=document.createElement(tag);node.textContent=text || '';if(cls)node.className=cls;return node;}
function validFacilityCoordinates(f) {return Number.isFinite(f.lat)&&Number.isFinite(f.lng)&&Math.abs(f.lat)<=90&&Math.abs(f.lng)<=180;}
function facilityPopup(f, showDetailLink=true) {
  const node=facilityNode('div','','facility-popup');
  node.append(facilityNode('strong',f.name),facilityNode('p',f.type_label,'small'),facilityNode('p',`${f.address || ''}, ${f.city || ''}`,'small muted'),facilityNode('p',`Telp: ${f.phone || '—'}`,'small muted'));
  const distance=facilityNode('p','','facility-result-distance');distance.id=`distance-marker-${f.id}`;node.append(distance);
  if(showDetailLink&&Number.isInteger(f.id)&&f.id>0){const link=facilityNode('a','Lihat Detail →','facility-result-link');link.href=`/facilities/${f.id}`;node.append(link);}
  return node;
}
function createFacilityMap(element,center,zoom) {
  if(typeof L==='undefined') {element.textContent='Peta tidak dapat dimuat. Gunakan daftar fasilitas untuk melihat informasi.';element.setAttribute('role','status');return null;}
  element.classList.add('skeleton');
  const map=L.map(element).setView(center,zoom);
  const status=facilityNode('p','Memuat peta…','small muted');status.setAttribute('role','status');element.after(status);
  const tiles=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);
  let errors=false;
  tiles.on('tileerror',()=>{element.classList.remove('skeleton');errors=true;status.textContent='Peta tidak tersedia sepenuhnya. Informasi fasilitas tetap dapat dibaca pada daftar.';});
  tiles.on('load',()=>{element.classList.remove('skeleton');if(!errors)status.textContent='';});
  return map;
}
function initFacilityListMap(mapId,facilitiesData) {
  const element=document.getElementById(mapId);
  const facilities=(facilitiesData || []).filter(validFacilityCoordinates);
  const map=element&&facilities.length?createFacilityMap(element,[facilities[0].lat,facilities[0].lng],11):null;
  if(element&&!facilities.length)element.textContent='Belum ada koordinat fasilitas untuk hasil pencarian ini.';
  if(map){facilities.forEach(f=>L.marker([f.lat,f.lng]).addTo(map).bindPopup(facilityPopup(f)));map.fitBounds(facilities.map(f=>[f.lat,f.lng]),{padding:[32,32],maxZoom:14});}
  const button=document.getElementById('btn-use-location'),feedback=document.getElementById('location-feedback');
  let userMarker=null;
  const status=(text,type='info')=>{if(feedback){feedback.style.display='block';feedback.className=`alert alert-${type}`;feedback.setAttribute('role','status');feedback.textContent=text;}};
  if(button)button.addEventListener('click',()=>{
    if(!navigator.geolocation){status('Geolokasi tidak didukung. Cari berdasarkan nama atau kota.','warning');return;}
    button.disabled=true;button.textContent='Mencari lokasi…';
    navigator.geolocation.getCurrentPosition(position=>{
      const lat=position.coords.latitude,lon=position.coords.longitude;
      if(map){if(userMarker)map.removeLayer(userMarker);userMarker=L.circleMarker([lat,lon],{radius:7,color:'#0B8179'}).addTo(map).bindPopup(facilityNode('strong','Posisi Anda'));map.setView([lat,lon],12);}
      facilities.forEach(f=>{const text=`± ${calculateDistanceKm(lat,lon,f.lat,f.lng)} km (perkiraan garis lurus)`;for(const prefix of ['distance-card-','distance-marker-']){const n=document.getElementById(prefix+f.id);if(n){n.textContent=text;n.style.display='inline-block';}}});
      status(facilities.length?'Lokasi digunakan untuk menghitung jarak fasilitas pada halaman ini. Koordinat tidak disimpan.':'Tidak ada fasilitas berkoordinat pada hasil ini. Ubah filter pencarian.','info');button.disabled=false;button.textContent='Gunakan Lokasi Saya';
    },()=>{button.disabled=false;button.textContent='Gunakan Lokasi Saya';status('Lokasi tidak dapat diakses. Anda tetap dapat mencari fasilitas secara manual.','warning');},{timeout:10000,enableHighAccuracy:false,maximumAge:0});
  });
}
function initFacilityDetailMap(mapId,facility) {
  const element=document.getElementById(mapId);if(!element)return;
  if(!validFacilityCoordinates(facility)){element.textContent='Lokasi peta belum tersedia untuk fasilitas ini.';return;}
  const map=createFacilityMap(element,[facility.lat,facility.lng],15);
  if(map)L.marker([facility.lat,facility.lng]).addTo(map).bindPopup(facilityPopup(facility,false)).openPopup();
}
