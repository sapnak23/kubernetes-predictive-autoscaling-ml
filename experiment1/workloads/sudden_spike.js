import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '4m', target: 5 },
    { duration: '1m', target: 150 },
    { duration: '5m', target: 150 },
    { duration: '1m', target: 10 },
    { duration: '3m', target: 10 },
    { duration: '1m', target: 120 },
    { duration: '3m', target: 120 },
    { duration: '2m', target: 0 },
  ],
};

export default function () {
  const response = http.get(__ENV.APP_URL);

  check(response, {
    'status is 200': (res) => res.status === 200,
  });

  sleep(0.2);
}