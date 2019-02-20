'use strict';

const SERVER_URL = 'http://localhost:3001/events';

function handleEvent (data, type) {
  $.ajax({
    url: SERVER_URL,
    type : 'POST',
    data: JSON.stringify({ data, type }),
    dataType: 'json',
    contentType: 'application/json' 
  });
}

$(() => {
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