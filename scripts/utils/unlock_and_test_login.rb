# Unlock and Test Login
email = 'cao.phan@galaxytechnology.vn'
password = 'OpenProject123!'

puts "--- Unlocking User: #{email} ---"
user = User.find_by(mail: email)

if user
  # Unlock
  user.failed_login_count = 0
  user.last_failed_login_on = nil
  user.force_password_change = false
  user.save(validate: false)
  puts "User unlocked and force_password_change disabled."
  
  # Test Login
  puts "--- Testing Login ---"
  # Try both email and login
  result_email = User.try_to_login(email, password)
  puts "Login result (Email): #{result_email ? 'SUCCESS' : 'FAILURE'}"
  
  result_login = User.try_to_login(user.login, password)
  puts "Login result (Login: #{user.login}): #{result_login ? 'SUCCESS' : 'FAILURE'}"

  if !result_email && !result_login
     puts "Login failed for both."
  end
else
  puts "User not found."
end
