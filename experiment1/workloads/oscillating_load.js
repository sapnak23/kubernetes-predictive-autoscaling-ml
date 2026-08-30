import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '3m', target: 20 },
    { duration: '3m', target: 80 },
    { duration: '3m', target: 20 },
    { duration: '3m', target: 120 },
    { duration: '3m', target: 20 },
    { duration: '3m', target: 80 },
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