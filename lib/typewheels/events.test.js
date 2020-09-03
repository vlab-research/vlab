const USER_ID = 1800244896727776
const PAGE_ID = 1051551461692797

const referral =  {
  recipient: { id: PAGE_ID },
  timestamp: 1542123799219,
  sender: { id: USER_ID },
  referral:
   { ref: 'form.FOO.foo.bar',
     source: 'SHORTLINK',
     type: 'OPEN_THREAD' } }

const payloadReferral =  {
  recipient: { id: PAGE_ID },
  timestamp: 1542123799219,
  sender: { id: USER_ID },
  postback: {
    payload: {referral: {ref:"form.FOO.foo.bar"}},
    title: 'whatever'
  }
}


// multiple choice response
const multipleChoice = {
  recipient: { id: PAGE_ID },
  timestamp: 1542116257642,
  sender: { id: USER_ID },
  postback:
   { payload: {value:true,ref:"foo"},
     title: 'I Accept' } }

const getStarted = {
  recipient: { id: PAGE_ID },
  timestamp: 1542116257642,
  sender: { id: USER_ID },
  postback: {
    payload: "get_started",
    referral: {
      ref: "form.FOO",
      source: "SHORTLINK",
      type: "OPEN_THREAD",
    },
    title: 'Get Started'
  }
}
// Text sent by user...
const text = {
  sender: { id: USER_ID },
  recipient: { id: PAGE_ID },
  timestamp: 1542116363617,
  message: { text: 'foo' } }


const sticker = {
  sender: { id: USER_ID },
  recipient: { id: PAGE_ID },
  timestamp: 1542116363617,
  message: { stickerId: 369239263222822, attachments: [{ type: 'image' }]} }

// Continue via quick reply...
const qr = {
  sender: { id: USER_ID },
  recipient: { id: PAGE_ID },
  timestamp: 20,
  message:
   { quick_reply: { payload: { value:"Continue",ref:"foo" }}}}

  // read
const read =  {
  sender: { id: USER_ID },
    recipient: { id: PAGE_ID },
    timestamp: 15,
    read: {watermark: 10 } }

const delivery = {
  sender: { id: USER_ID },
  recipient: { id: PAGE_ID },
  timestamp: 16,
  delivery:
   { watermark: 15 }}

const optin = {
  sender: { id: USER_ID },
  recipient: { id: PAGE_ID },
  timestamp: 25,
  optin: { type: 'one_time_notif_req',
           one_time_notif_token: 'FOOBAR',
           payload: { ref: 'foo' }} }

  // is echo
const echo = {
  sender: { id: PAGE_ID },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: { "ref": "foo" },
    text: 'Whatsupp welcome you agree or what?' } }

const statementEcho = {
  sender: { id: PAGE_ID },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: { "ref": "bar", "type": "statement" },
    text: 'Whatsupp, welcome.' } }

const tyEcho = {
  sender: { id: PAGE_ID },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: { "ref": "baz", "type": "thankyou_screen" },
    text: 'Thanks' } }


const fakeEcho = {
  sender: { id: PAGE_ID },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { fake_echo: true,
    is_echo: true,
    metadata: { "ref": "foo", "type": "statement" },
    text: 'Whatsupp, welcome.' } }

const repeatEcho = {
  sender: { id: PAGE_ID },
  recipient: { id: USER_ID },
  timestamp: 5,
  message:
  { is_echo: true,
    metadata: {ref: "bar", repeat: "true" },
    text: 'Whatsupp, welcome.' } }


const syntheticBail = {
  source: 'synthetic',
  event: {
    type: 'bailout',
    value: {
      form: 'BAR'
    }
  },
  user: USER_ID,
  page: PAGE_ID,
  timestamp: 20
}

const syntheticRedo = {
  source: 'synthetic',
  event: {
    type: 'redo'
  },
  user: USER_ID,
  page: PAGE_ID,
  timestamp: 20
}


const syntheticPR = {
  source: 'synthetic',
  event: {
    type: 'platform_response',
    value: {
      response: 'OK',
      metadata: ''
    }
  },
  user: USER_ID,
  page: PAGE_ID,
  timestamp: 20
}

const synthetic = (event, more={}) => {
  return {source: 'synthetic',
          user: USER_ID,
          page: PAGE_ID,
          timestamp: 20,
          event,
          ...more}
}

const reaction = { sender: { id: '1972130092884542' },
  recipient: { id: USER_ID },
  timestamp: 1581454140135,
  reaction: {
     action: 'react',
     emoji: '😠',
     reaction: 'angry' },
  source: 'messenger'
}



module.exports = { getStarted, echo, fakeEcho, tyEcho, statementEcho, repeatEcho, delivery, read, qr, text, sticker, multipleChoice, referral, reaction, USER_ID, syntheticBail, syntheticPR, optin, payloadReferral, syntheticRedo, synthetic }
