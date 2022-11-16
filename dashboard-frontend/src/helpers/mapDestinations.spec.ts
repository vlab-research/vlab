import destinations from '../pages/NewStudyPage/configs/destinations/destinations';
import mapDestinations from './mapDestinations';

describe('mapDestinations', () => {
  it('maps over an array of destinations and for each option it assigns a label and name', () => {
    const expectation = [
      { name: 'fly_messenger', label: 'Fly Messenger' },
      { name: 'typeform', label: 'Typeform' },
      { name: 'curious_learning', label: 'Curious Learning' },
    ];

    const res = mapDestinations(destinations);

    expect(res).toStrictEqual(expectation);
  });
});
