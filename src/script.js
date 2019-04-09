'use strict';

const SERVER_URL = '{{{SERVER_URL}}}';
const params = new URLSearchParams(window.location.search);
const videoId = params.get('id');
let psid;

function handleEvent(data, eventType) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', SERVER_URL);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(JSON.stringify({ data, eventType, psid }));
}

window.extAsyncInit = function () {
  MessengerExtensions.getUserID('{{{APP_ID}}}',
    function success(thread_context) {
      psid = thread_context.psid;
    },
    function error(err) {
      console.error(err);
    }
  );
};

document.addEventListener('DOMContentLoaded', () => {
  const options = {
    id: videoId,
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
