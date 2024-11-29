print('Patching generated bundle-index.css…')
with open('../ottm/static/ottm/bundle-index.css', mode='r+') as f:
    output = f.read().replace('/bundle-materialdesignicons-webfont', '/static/ottm/bundle-materialdesignicons-webfont')
    f.seek(0)
    f.write(output)
    f.truncate()
