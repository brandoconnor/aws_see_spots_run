name 'aws_see_spots_run'
maintainer "Brandon O'Connor"
maintainer_email 'brandoconnor@gmail.com'
license 'Apache 2.0'
description 'Installs/Configures aws_see_spots_run'\
            'a spot instance management platform.'
long_description IO.read(File.join(File.dirname(__FILE__), 'README.md'))
version '0.2.0'
depends 'python'

%w(
  ubuntu
  debian
  centos
  redhat
  fedora
  amazon
).each do |os|
  supports os
end
