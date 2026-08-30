import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    // Initial low and irregular traffic
    { duration: '3m', target: 8 },
    { duration: '2m', target: 25 },
    { duration: '3m', target: 12 },

    // First unpredictable burst
    { duration: '1m', target: 110 },
    { duration: '3m', target: 110 },
    { duration: '2m', target: 35 },

    // Medium irregular demand
    { duration: '3m', target: 60 },
    { duration: '2m', target: 18 },
    { duration: '3m', target: 85 },
    { duration: '2m', target: 30 },

    // Larger sudden burst
    { duration: '1m', target: 160 },
    { duration: '3m', target: 160 },
    { duration: '2m', target: 45 },

    // Rapid fluctuations
    { duration: '2m', target: 95 },
    { duration: '2m', target: 20 },
    { duration: '2m', target: 130 },
    { duration: '2m', target: 40 },
    { duration: '2m', target: 75 },

    // Quiet period followed by another burst
    { duration: '3m', target: 10 },
    { duration: '1m', target: 145 },
    { duration: '3m', target: 145 },
    { duration: '2m', target: 25 },

    // Final irregular section and cooldown
    { duration: '3m', target: 70 },
    { duration: '2m', target: 15 },
    { duration: '2m', target: 100 },
    { duration: '3m', target: 0 },
  ],

  thresholds: {
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  const response = http.get(__ENV.APP_URL);

  check(response, {
    'status is 200': (res) => res.status === 200,
  });

  // Random think time makes request arrival less perfectly regular.
  sleep(Math.random() * 0.8 + 0.1);
}