// https://m.me/testvirtuallab?ref=form.LDfNCy

const user = { 
    id: '2036910886400628',
    name : 'Leonardo Di Vittorio',
    first_name : 'Leonardo',
    last_name : 'Di Vittorio' };

const referral = { 
  id: '935593143497601',
  time: Date.now(),
  messaging:[ 
  { recipient: { id: '935593143497601' },
    timestamp: Date.now(),
    sender: { id: '2036910886400628' },
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

const delivery = {
  id: '935593143497601',
  time: 1551887302071,
  messaging: [
  { sender: { id: '2036910886400628' },
    recipient: { id: '935593143497601' },
    timestamp: 1551887302059,
    delivery: { watermark: 1551887299229, seq: 0 } } ] };

const read = { 
  id: '935593143497601',
  time: 1551887302265,
  messaging: [
  { sender: { id: '2036910886400628' },
    recipient: { id: '935593143497601' },
    timestamp: 1551887302260,
    read: { watermark: 1551887299229, seq: 0 } } ] }

// same read message with different timestamp

const accept = {
  id: '935593143497601',
  time: 1551887303666,
  messaging: [
  { sender: { id: '935593143497601' },
    recipient: { id: '2036910886400628' },
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
            payload: '{"value":false,"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}' } ] } } ] } } ] }

// delivery message with different timestamp x3
// mids: [ 'iahSu_Be1nwB0pi0T7BGm8XudRc1e6dWdtHiSuxSf8AiV4vXTAKae7XxYUu4MJLRGzMzuEno4WzjjFU3GjbgbQ' ]
// watermark: 1551887302933

// read message 
// watermark: 1551887302933

const postback = { 
  id: '935593143497601',
  time: 1551887308298,
  messaging:[
  { recipient: { id: '935593143497601' },
    timestamp: 1551887308298,
    sender: { id: '2036910886400628' },
    postback: { 
      payload: '{"value":true,"ref":"f37a882b-8cd3-4d13-9457-1ee17448f4b5"}',
      title: 'I Accept' } } ] };


const message = { 
  id: '935593143497601',
  time: 1551887310912,
  messaging: [
  { sender: { id: '935593143497601' },
    recipient: { id: '2036910886400628' },
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

// delivery message with different timestamp x3
// mids: [ 'eFG8cGL4KY_3EJHEafc8DcXudRc1e6dWdtHiSuxSf8BnO50lky7UUKwZ0xLTLqtSrmz7zpGuV0HNcZ2TNKPy_w' ]
// watermark: 1551887310252
  
// read message 
// watermark: 1551887310252

const postback2 = { 
  id: '935593143497601',
  time: 1551887313699,
  messaging:[
  { recipient: { id: '935593143497601' },
    timestamp: 1551887313699,
    sender: { id: '2036910886400628' },
    postback: { 
      payload: '{"value":true,"ref":"a072e75f-0f04-4e9c-91d2-ffd15aa3e82d"}',
      title: 'Yes' } } ] };


const message2 = {
  id: '935593143497601',
  time: 1551887315982,
  messaging:[
  { sender: { id: '935593143497601' },
    recipient: { id: '2036910886400628' },
    timestamp: 1551887315422,
    message: {
      is_echo: true,
      app_id: 790352681363186,
      metadata: '{"type":"statement","ref":"acc2f381-405f-4c84-9cd0-889312b8b64c"}',
      mid: '54VnGmA899_StdKwELhSRsXudRc1e6dWdtHiSuxSf8A53BI_onuS6V3H3UJVCMrZHj5ErDE5J1EsiEZPxG_E9w',
      seq: 89475,
      text: 'Thanks' } } ] };
        

// delivery message with different timestamp x3
// mids: [ '54VnGmA899_StdKwELhSRsXudRc1e6dWdtHiSuxSf8A53BI_onuS6V3H3UJVCMrZHj5ErDE5J1EsiEZPxG_E9w' ]
// watermark: 1551887315422
  
// read message 
// watermark: 1551887315422

const message3 = { 
  id: '935593143497601',
  time: 1551887317961,
  messaging:[
  { sender: { id: '935593143497601' },
    recipient: { id: '2036910886400628' },
    timestamp: 1551887317359,
    message:{ 
      is_echo: true,
      app_id: 790352681363186,
      metadata: '{"type":"thankyou_screen","ref":"default_tys"}',
      mid: 'LGNLwciAQy9xOqw9AZ4uTsXudRc1e6dWdtHiSuxSf8D6kjfLuomB-6cGZKvyVHJxKQB17AcFhC64nD5kzSA6hg',
      seq: 89478,
      text: 'Done! Your information was sent perfectly.' } } ] };


// delivery message with different timestamp x3
// mids: [ 'LGNLwciAQy9xOqw9AZ4uTsXudRc1e6dWdtHiSuxSf8D6kjfLuomB' ]
// watermark: 1551887317359
  
// read message 
// watermark: 1551887317359

module.exports = { user, referral, getStarted, delivery, read, accept, postback, message, postback2, message2, message3}