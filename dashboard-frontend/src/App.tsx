import React from 'react';
import { createFakeStudy } from './fixtures/study';

function App() {
  const study = createFakeStudy({
    creationDate: Date.now(),
    desiredParticipants: 24000,
    numOfDifferentStrata: 10,
    desiredParticipantsPerStrata: 2400,
    totalHoursOfData: 24,
  });

  return (
    <div className="bg-gray-200 min-h-screen p-8 flex flex-col items-center justify-center antialiased">
      <div>
        <h1>Smoke Test</h1>
        <pre>{JSON.stringify(study, null, 2)}</pre>
      </div>
    </div>
  );
}

export default App;
