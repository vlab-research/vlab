// https://m.me/testvirtuallab?ref=form.LDfNCy
const uuid = require('uuid')

const user = { 
    id: uuid(),
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
          payload: '{"value":true,"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}' },
        { type: 'postback',
          title: 'I don\'t Accept',
          payload: '{"value":false,"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}' } ] } },
  metadata: '{"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}' }

const acceptEcho = {
  id: '935593143497601',
  time: 1551887303666,
  messaging: [
  { sender: { id: '935593143497601' },
    recipient: { id: user.id },
    timestamp: 1551887302933,
    message:{ 
      is_echo: true,
      app_id: 790352681363186,
      metadata: '{"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}',
      mid: 'iahSu_Be1nwB0pi0T7BGm8XudRc1e6dWdtHiSuxSf8AiV4vXTAKae7XxYUu4MJLRGzMzuEno4WzjjFU3GjbgbQ',
      seq: 89465,
      text: 'Hello, do you agree to take this survey?',
      attachments:[
      { title: '',
        url: null,
        type: 'template',
        payload:{ 
          template_type: 'button',
          buttons:[
          { type: 'postback',
            title: 'I Accept',
            payload: '{"value":true,"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}' },
          { type: 'postback',
            title: 'I don\'t Accept',
            payload: '{"value":false,"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}' } ] } } ] } } ] };

const acceptPostback = { 
  id: '935593143497601',
  time: 1551887308298,
  messaging:[
  { recipient: { id: '935593143497601' },
    timestamp: 1551887308298,
    sender: { id: user.id },
    postback: { 
      payload: '{"value":true,"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}',
      title: 'I Accept' } } ] };

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

const questionEcho = { 
  id: '935593143497601',
  time: 1551887310912,
  messaging: [
  { sender: { id: '935593143497601' },
    recipient: { id: user.id },
    timestamp: 1551887310252,
    message: { 
      is_echo: true,
      app_id: 790352681363186,
      metadata: '{"ref":"a072e75f-0f04-4e9c-91d2-ffd15aa3e82d"}',
      mid:
      'eFG8cGL4KY_3EJHEafc8DcXudRc1e6dWdtHiSuxSf8BnO50lky7UUKwZ0xLTLqtSrmz7zpGuV0HNcZ2TNKPy_w',
      seq: 89470,
      text: 'Are you fun?',
      attachments: [
      { title: '',
      url: null,
      type: 'template',
      payload: { 
        template_type: 'button',
        buttons:[
        { type: 'postback',
          title: 'Yes',
          payload:
            '{"value":true,"ref":"a072e75f-0f04-4e9c-91d2-ffd15aa3e82d"}' },
        { type: 'postback',
          title: 'No',
          payload: '{"value":false,"ref":"a072e75f-0f04-4e9c-91d2-ffd15aa3e82d"}' } ] } } ] } } ] };

const questionPostbackNo = { 
  id: '935593143497601',
  time: 1551887313699,
  messaging:[
  { recipient: { id: '935593143497601' },
    timestamp: 1551887313699,
    sender: { id: user.id },
    postback: { 
      payload: '{"value":true,"ref":"a072e75f-0f04-4e9c-91d2-ffd15aa3e82d"}',
      title: 'No' } } ] };

const questionPostbackYes = { 
  id: '935593143497601',
  time: 1551887313699,
  messaging:[
  { recipient: { id: '935593143497601' },
    timestamp: 1551887313699,
    sender: { id: user.id },
    postback: { 
      payload: '{"value":true,"ref":"a072e75f-0f04-4e9c-91d2-ffd15aa3e82d"}',
      title: 'Yes' } } ] };

const funMessage = { 
  text: "You are fun! Why?",
  metadata:'{"ref":"51f08eef-5455-43af-87c6-a34983e2b0a6"}' }

const funEcho = {
  id: '935593143497601',
  time: 1551887315982,
  messaging:[
  { sender: { id: '935593143497601' },
    recipient: { id: user.id },
    timestamp: 1551887315422,
    message: {
      is_echo: true,
      app_id: 790352681363186,
      metadata: '{"ref":"51f08eef-5455-43af-87c6-a34983e2b0a6"}',
      mid: '54VnGmA899_StdKwELhSRsXudRc1e6dWdtHiSuxSf8A53BI_onuS6V3H3UJVCMrZHj5ErDE5J1EsiEZPxG_E9w',
      seq: 89475,
      text: "You are fun! Why?" } } ] };

const funPostback = { 
  id: '935593143497601',
  time: 1551887313699,
  messaging:[
  { recipient: { id: '935593143497601' },
    timestamp: 1551887313699,
    sender: { id: user.id },
    postback: { 
      payload: '{"value":true,"ref":"51f08eef-5455-43af-87c6-a34983e2b0a6"}',
      title: 'LOL' } } ] };

const boringMessage = { 
  text: "You are boring! Sorry, you can't play.",
  metadata:'{"type":"statement","ref":"acc2f381-405f-4c84-9cd0-889312b8b64c"}' }

const boringEcho = {
  id: '935593143497601',
  time: 1551887315982,
  messaging:[
  { sender: { id: '935593143497601' },
    recipient: { id: user.id },
    timestamp: 1551887315422,
    message: {
      is_echo: true,
      app_id: 790352681363186,
      metadata: '{"type":"statement","ref":"acc2f381-405f-4c84-9cd0-889312b8b64c"}',
      mid: '54VnGmA899_StdKwELhSRsXudRc1e6dWdtHiSuxSf8A53BI_onuS6V3H3UJVCMrZHj5ErDE5J1EsiEZPxG_E9w',
      seq: 89475,
      text: "You are boring! Sorry, you can't play." } } ] };

const thanksMessage = { 
  text: 'Thanks',
  metadata:'{"type":"statement","ref":"acc2f381-405f-4c84-9cd0-889312b8b64c"}' }

const thanksEcho = {
  id: '935593143497601',
  time: 1551887315982,
  messaging:[
  { sender: { id: '935593143497601' },
    recipient: { id: user.id },
    timestamp: 1551887315422,
    message: {
      is_echo: true,
      app_id: 790352681363186,
      metadata: '{"type":"statement","ref":"acc2f381-405f-4c84-9cd0-889312b8b64c"}',
      mid: '54VnGmA899_StdKwELhSRsXudRc1e6dWdtHiSuxSf8A53BI_onuS6V3H3UJVCMrZHj5ErDE5J1EsiEZPxG_E9w',
      seq: 89475,
      text: 'Thanks' } } ] };
       
const endMessage = { 
  text: 'Done! Your information was sent perfectly.',
  metadata: '{"type":"thankyou_screen","ref":"default_tys"}' }

const endEcho = { 
  id: '935593143497601',
  time: 1551887317961,
  messaging:[
  { sender: { id: '935593143497601' },
    recipient: { id: user.id },
    timestamp: 1551887317359,
    message:{ 
      is_echo: true,
      app_id: 790352681363186,
      metadata: '{"type":"thankyou_screen","ref":"default_tys"}',
      mid: 'LGNLwciAQy9xOqw9AZ4uTsXudRc1e6dWdtHiSuxSf8D6kjfLuomB-6cGZKvyVHJxKQB17AcFhC64nD5kzSA6hg',
      seq: 89478,
      text: 'Done! Your information was sent perfectly.' } } ] };

module.exports = { 
  user, 
  referral,
  getStarted,
  acceptMessage,
  acceptEcho,
  acceptPostback, 
  questionMessage, 
  questionEcho, 
  questionPostbackNo,
  questionPostbackYes,
  funMessage,
  funEcho,
  funPostback,
  boringMessage,
  boringEcho,
  thanksMessage,
  thanksEcho,
  endMessage,
  endEcho
}