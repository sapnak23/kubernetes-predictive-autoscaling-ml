import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5m', target: 10 },
    { duration: '5m', target: 40 },
    { duration: '5m', target: 80 },
    { duration: '3m', target: 20 },

    { duration: '2m', target: 140 },
    { duration: '5m', target: 140 },
    { duration: '3m', target: 20 },

    { duration: '4m', target: 70 },
    { duration: '4m', target: 25 },
    { duration: '4m', target: 100 },
    { duration: '4m', target: 30 },

    { duration: '3m', target: 120 },
    { duration: '3m', target: 15 },
    { duration: '3m', target: 80 },
    { duration: '3m', target: 0 },
  ],
};

export default function () {
  const response = http.get(__ENV.APP_URL);

  check(response, {
    'status is 200': (res) => res.status === 200,
  });

  sleep(0.2);
}