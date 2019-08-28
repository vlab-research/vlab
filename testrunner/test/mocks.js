// https://m.me/testvirtuallab?ref=form.LDfNCy
const uuid = require('uuid');
const PAGE_ID = '935593143497601';

function _baseMessage(userId, extra) {
  return {
    id: uuid(),
    time: Date.now(),
    messaging: [{
      sender: { id: PAGE_ID } ,
      recipient: { id: userId },
      timestamp: Date.now(),
      ...extra
    }]
  }
}

function makeEcho(message, userId) {
  const extra =  {
    message: {
      is_echo: true,
      metadata: message.metadata,
      text: message.text || message.attachment.payload.text,
    }
  }

  return _baseMessage(userId, extra)
}

function makePostback(message, userId, idx) {

  const button = message.attachment.payload.buttons[idx]
  const postback = {payload: button.payload, title: button.title }

  return _baseMessage(userId, {postback})
}

function makeTextResponse(userId, text) {
  return _baseMessage(userId, { message: { text }})
}


function makeMocks(id) {
  const user = {
    id: id,
    name : 'Leonardo Di Vittorio',
    first_name : 'Leonardo',
    last_name : 'Di Vittorio' };

  const referral = {
    id: '935593143497601',
    time: Date.now(),
    messaging:[
      { recipient: { id: '935593143497601' },
        timestamp: Date.now(),
        sender: { id: user.id },
        referral: {
          ref: 'form.LDfNCy',
          source: 'SHORTLINK',
          type: 'OPEN_THREAD' } } ] };

  const getStarted = {
    id: '935593143497601',
    time: 1551887299307,
    messaging:[
      { recipient: { id: '1051551461692797' },
        timestamp: 1542116257642,
        sender: { id: '1800244896727776' },
        postback: {
          payload: "get_started",
          referral: {
            ref: "form.FOO",
            source: "SHORTLINK",
            type: "OPEN_THREAD",
          },
          title: 'Get Started' } } ] };

  const acceptMessage =  {
    attachment: {
      type: 'template',
      payload:
      { template_type: 'button',
        text: 'Hello, do you agree to take this survey?',
        buttons: [{
          type: 'postback',
          title: 'I Accept',
          payload: '{"value":true,"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}'
        },{
          type: 'postback',
          title: 'I don\'t Accept',
          payload: '{"value":false,"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}' } ] } },
    metadata: '{"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}' }

  const questionMessage = {
    attachment: {
      type: 'template',
      payload:
      { template_type: 'button',
        text: 'Are you fun?',
        buttons: [
          { type: 'postback',
            title: 'Yes',
            payload:
            '{"value":true,"ref":"a072e75f-0f04-4e9c-91d2-ffd15aa3e82d"}' },
          { type: 'postback',
            title: 'No',
            payload: '{"value":false,"ref":"a072e75f-0f04-4e9c-91d2-ffd15aa3e82d"}' }] } },
    metadata: '{"ref":"a072e75f-0f04-4e9c-91d2-ffd15aa3e82d"}' }

  const funMessage = {
    text: "You are fun! Why?",
    metadata:'{"ref":"51f08eef-5455-43af-87c6-a34983e2b0a6"}' }

  const boringMessage = {
    text: "You are boring! Sorry, you can't play.",
    metadata:'{"type":"statement","ref":"8b67d18c-cda5-4936-83ea-bda055cf20dc"}' }

  const thanksMessage = {
    text: 'Thanks',
    metadata:'{"type":"statement","ref":"acc2f381-405f-4c84-9cd0-889312b8b64c"}' }

  const endMessage = {
    text: 'Done! Your information was sent perfectly.',
    metadata: '{"type":"thankyou_screen","ref":"default_tys"}' }

  return {
    user,
    referral,
    getStarted,
    acceptMessage,
    questionMessage,
    funMessage,
    boringMessage,
    thanksMessage,
    endMessage,
  }
}

module.exports = {
  makeMocks,
  makeEcho,
  makePostback,
  makeTextResponse
}
