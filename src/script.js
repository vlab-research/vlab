'use strict';

const SERVER_URL = 'http://localhost:3001/events';

function handleEvent(data, eventType) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', SERVER_URL);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(JSON.stringify({ data, eventType }));
}
document.addEventListener('DOMContentLoaded', () => {
  const options = {
    id: 280815263,
    width: 800
  };
  const player = new Vimeo.Player('vimeoVideo', options);

  player.on('error', data => handleEvent(data, 'error'));

  player.on('loaded', data => handleEvent(data, 'loaded'));

  player.on('play', data => handleEvent(data, 'play'));

  player.on('pause', data => handleEvent(data, 'pause'));

  player.on('ended', data => handleEvent(data, 'ended'));
});