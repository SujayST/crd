echo "Switching to brnch master"
git checkout master

echo "Building app.."
npm run build

echo "Deploying files to server..."
scp -r build/* root@nginx:10.219.96.135:/var/www/10.219.96.135/

echo "Successful!"
