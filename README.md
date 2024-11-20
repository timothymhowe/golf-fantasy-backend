# Golf Fantasy Backend

Backend API for Golf Fantasy, built with Flask.

## Setup
1. Create virtual environment: `python -m venv .venv`
2. Activate: `source .venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Create `.env` file with required environment variables
5. Run development server: `gunicorn -c gunicorn.conf.py "run:app"`

## Firebase Authentication

Firebase Authentication is used for user authentication in the Golf Fantasy website. It provides a secure and easy-to-use authentication system, allowing users to sign up, sign in, and manage their account credentials.

## Database: MySQL

The Golf Fantasy website utilizes a MySQL database for storing and managing data. Here is a placeholder description of the DB structure:

- `golfer` : Stores information about golf players, including their name, nationality, and ranking.
- `league` : Represents the fantasy leagues created by users, containing details like league name, member, commisioner, and owner.
- `user` : Contains information about registered users, such as their username, email, link to their avatar photo, etc.
- `roles` : list of roles, permissions associated with those roles



## More Info

For more information on Next.js, Flask, Firebase Authentication, and Firebase Storage, refer to the following resources:

- [Next.js Documentation](https://nextjs.org/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Firebase Authentication Documentation](https://firebase.google.com/docs/auth)
<!-- - [Firebase Storage Documentation](https://firebase.google.com/docs/storage)
This is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.js`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/basic-features/font-optimization) to automatically optimize and load Inter, a custom Google Font.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js/) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/deployment) for more details. -->
### Run the API

To run the Flask API in development mode:
1. From the root directory, run `source .venv/bin/activate`
2. Navigate to the `src/api` directory:
3. Run `flask run dev`
4. Hopefully it works


### Run the frontend

To run the frontend in development mode:

1. Navigate to the root directory
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`


## TODO List

### Performance Optimizations
- [ ] Optimize golfer photo loading in dropdown
  - [ ] Implement client-side caching for Firebase Storage URLs
  - [ ] Preload images for frequently accessed golfers
  - [ ] Configure Firebase Storage CDN settings
  - [ ] Add loading states/skeletons for images
  - [ ] Consider implementing lazy loading for off-screen images
  - [ ] Investigate batch loading strategies for golfer photos

- [ ] Optimize dashboard data loading
  - [ ] Consolidate multiple API calls into single dashboard endpoint
  - [ ] Implement server-side data aggregation
  - [ ] Add proper caching strategy for dashboard data
  - [ ] Consider implementing real-time updates for leaderboard
  - [ ] Add loading states for individual widgets
  - [ ] Monitor and optimize database queries

- [ ] Move scoring system to database
  - Currently hardcoded in `src/api/jobs/calculate_points/calculate_points.py`
  - Should be configurable per league/season
  - Reference tables: League, ScoringRuleset, ScoringRule

  ### Authentication & Onboarding
- [ ] Create user onboarding flow
  - [ ] Design simple registration form
  - [ ] Implement Firebase authentication
  - [ ] Add email verification
  - [ ] Create user profile in database after successful auth
  - [ ] Redirect to league selection/creation

### New Homepage Widgets
- [ ] User Pick History Widget
  - [ ] Create component to display all historical picks
  - [ ] Show tournament name, date, golfer picked, and result
  - [ ] Add sorting/filtering options
  - [ ] Include visual indicators for good/bad picks

- [ ] League Standings Timeline Visualization
  - [ ] Create line graph component using D3 or Chart.js
  - [ ] Plot each league member's points over time
  - [ ] Add interactive tooltips showing exact scores
  - [ ] Include tournament markers on x-axis
  - [ ] Add legend for member identification
  - [ ] Implement zoom/pan for longer timeframes

- [ ] Cache league standings
  - [ ] Create LeagueStandingsCache table
  - [ ] Update cache when tournament scores change
  - [ ] Update cache when league membership changes
  - [ ] Add cache timestamp tracking
  - [ ] Add cache invalidation logic
  - [ ] Add monitoring for cache freshness


### API Integrations
- [ ] Implement Firestore caching layer for DataGolf API
  - [ ] Create Firestore collections for:
    - [ ] Tournament fields
    - [ ] Live scoring data
    - [ ] Player rankings
    - [ ] Tournament schedules
    - [ ] Historical results
  - [ ] Implement API-to-Firestore sync jobs
  - [ ] Update API endpoints to read from Firestore first
  - [ ] Add timestamp tracking for data freshness
  - [ ] Implement intelligent refresh logic
  - [ ] Add backup/restore functionality
  - [ ] Set up monitoring for sync jobs

- [ ] Migrate to DataGolf API as primary data source
  - [ ] Replace SportContent API calls with DataGolf equivalents
  - [ ] Implement comprehensive player mapping system
  - [ ] Add DataGolf player IDs to golfer table
  - [ ] Update tournament field management
  - [ ] Update live scoring integration
  - [ ] Add historical data import
  - [ ] Add odds and statistics integration
  - [ ] Implement proper error handling for API limits


### Security Improvements

#### Firebase Storage Rules
Current rules allow public read access to all profile images. Need to implement more granular access:
- Restrict profile image access to:
  - The image owner
  - Members of the same league
  - League commissioners
- Current temporary rules:

### Technical Debt & Improvements
- [ ] Implement robust API client solution
  - [ ] Replace direct fetch calls with TanStack Query
  - [ ] Set up centralized API client service
  - [ ] Add request/response interceptors
  - [ ] Implement proper error handling
  - [ ] Add request caching
  - [ ] Add request deduplication
  - [ ] Add retry logic
  - [ ] Add request cancellation
  - [ ] Add proper TypeScript types
  - [ ] Set up monitoring and logging

