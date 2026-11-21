const express = require('express');
const { MongoClient } = require('mongodb');
const os = require('os');
const path = require('path');

const PORT = process.env.PORT || 3000;
const MONGO_URL = process.env.MONGO_URL;          // no hard-coded host/password
const POD_NAME = process.env.HOSTNAME || os.hostname();

if (!MONGO_URL) {
  console.error('MONGO_URL environment variable is not set');
  process.exit(1);
}

const client = new MongoClient(MONGO_URL, { serverSelectionTimeoutMS: 2000 });
const calculations = () => client.db().collection('calculations'); // db name comes from MONGO_URL

function getPodIp() {
  for (const list of Object.values(os.networkInterfaces())) {
    for (const i of list) {
      if (i.family === 'IPv4' && !i.internal) return i.address;
    }
  }
  return 'unknown';
}

function isPositive(x) {
  return typeof x === 'number' && Number.isFinite(x) && x > 0;
}

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// POST /api/emi
app.post('/api/emi', async (req, res) => {
  const P = Number(req.body.principal ?? req.body.P);
  const rate = Number(req.body.rate);
  const n = Number(req.body.months ?? req.body.n);

  if (!isPositive(P) || !isPositive(rate) || !isPositive(n) || !Number.isInteger(n)) {
    return res.status(400).json({ error: 'principal, rate and months must be positive numbers (months must be a whole number)' });
  }

  const r = rate / 12 / 100;
  const factor = Math.pow(1 + r, n);
  const emi = (P * r * factor) / (factor - 1);
  const totalPayment = emi * n;
  const totalInterest = totalPayment - P;
  const round2 = (v) => Math.round(v * 100) / 100;

  const doc = {
    principal: P, rate, months: n,
    emi: round2(emi),
    servedBy: POD_NAME,
    createdAt: new Date()
  };

  try {
    await calculations().insertOne(doc);
  } catch (err) {
    console.error('DB write failed:', err.message);
    return res.status(503).json({ error: 'database unavailable' });
  }

  res.json({
    emi: round2(emi),
    totalPayment: round2(totalPayment),
    totalInterest: round2(totalInterest),
    pod: { name: POD_NAME, ip: getPodIp() }
  });
});

// GET /api/history  (last 10, newest first)
app.get('/api/history', async (req, res) => {
  try {
    const rows = await calculations().find({}, { projection: { _id: 0 } })
      .sort({ createdAt: -1 }).limit(10).toArray();
    res.json(rows);
  } catch (err) {
    res.status(503).json({ error: 'database unavailable' });
  }
});

// GET /health  -> 200 only if MongoDB is reachable
app.get('/health', async (req, res) => {
  try {
    await client.db().command({ ping: 1 });
    res.status(200).send('OK');
  } catch (err) {
    res.status(503).send('MongoDB unreachable');
  }
});

app.listen(PORT, () => console.log(`EMI app listening on ${PORT}, pod=${POD_NAME}`));
