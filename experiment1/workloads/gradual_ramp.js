import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 10 },
    { duration: '2m', target: 25 },
    { duration: '2m', target: 50 },
    { duration: '2m', target: 80 },
    { duration: '2m', target: 40 },
    { duration: '1m', target: 10 },
    { duration: '1m', target: 0 },
  ],
};

export default function () {
  const response = http.get(__ENV.APP_URL);

  check(response, {
    'status is 200': (res) => res.status === 200,
  });

  sleep(0.2);
}