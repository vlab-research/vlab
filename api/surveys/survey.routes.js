const router = require('express').Router();
const controller = require('./survey.controller');

// make by teamid
// validate user has access to team
// make /teams/:id/surveys route.
// POST and GET ALL move to that route

// seperate /surveys.getBy route
// is only for "internal" users
// (other server!!) -- change from 
// auth0 API auth to custom setup.

router.post('/', controller.postOne);
router.get('/', controller.getBy, controller.getAll);

module.exports = router;
