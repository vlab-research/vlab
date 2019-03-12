'use strict';

const SERVER_URL = '{{{SERVER_URL}}}';
const params = new URLSearchParams(window.location.search);
const id = params.get('id');

function handleEvent(data, eventType) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', SERVER_URL);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(JSON.stringify({ data, eventType }));
}

document.addEventListener('DOMContentLoaded', () => {
  const options = {
    id,
    width: 800
  };
  const player = new Vimeo.Player('vimeoVideo', options);

  player.ready().then(() => {
    player.on('ended', data => handleEvent(data, 'ended'));
  
    player.on('error', data => handleEvent(data, 'error'));
    
    player.on('pause', data => handleEvent(data, 'pause'));
    
    player.on('play', data => handleEvent(data, 'play'));
    
    player.on('playbackratechange', data => handleEvent(data, 'playbackratechange'));
    
    player.on('seeked', data => handleEvent(data, 'seeked'));
  
    player.on('volumechange', data => handleEvent(data, 'volumechange'));
  }).catch((err) => {
    console.error(err);
    document.querySelector('body').innerHTML = `<p>Video not found</p>`;
  });

});
