# Create Recovery Admin
email = 'recovery@example.com'
login = 'recovery_admin'
password = 'Recovery123!'

u = User.find_by(login: login)
if u
  u.destroy
end

u = User.new(mail: email, login: login, firstname: 'Recovery', lastname: 'Admin', admin: true, status: 1, language: 'en')
u.password = password
u.password_confirmation = password
u.force_password_change = false
if u.save
  puts "Recovery User Created."
  puts "Login: #{login}"
  puts "Password: #{password}"
else
  puts "Failed: #{u.errors.full_messages}"
end
