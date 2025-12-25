# Diagnose user login issues
email = 'cao.phan@galaxytechnology.vn'
login = 'cao.phan'

puts "--- Diagnosing User: #{email} ---"
user = User.find_by(mail: email)

if user.nil?
  puts "User NOT FOUND by email."
  user = User.find_by(login: login)
  if user
      puts "User FOUND by login: #{user.login} (ID: #{user.id})"
  else
      puts "User NOT FOUND by login either."
      exit 1
  end
else
  puts "User FOUND by email: #{user.login} (ID: #{user.id})"
end

puts "Status: #{user.status} (1=Active, 2=Registered, 3=Locked)"
puts "Auth Source ID: #{user.auth_source_id.inspect} (Should be nil for internal auth)"
puts "Password Digest Present: #{user.password_digest.present?}"
puts "Failed Login Count: #{user.failed_login_count}"
puts "Last Failed Login: #{user.last_failed_login_on}"
puts "Force Password Change: #{user.force_password_change}"
puts "Identity URL: #{user.identity_url.inspect}"
puts "Type: #{user.type}"

# Attempt to validate password (if we knew the hash mechanism, but we can't easily check 'valid_password?' without the plaintext, wait, we can try to set it and see if errors occur)
# actually user.valid_password?('OpenProject123!') might work in console
puts "--- Auth Check ---"
if user.try(:check_password?, 'OpenProject123!')
    puts "Password 'OpenProject123!' is VALID according to check_password?"
else
    puts "Password 'OpenProject123!' is INVALID according to check_password?"
end

# Check if maybe there are duplicate users?
users = User.where(mail: email)
puts "User count with this email: #{users.count}"
users = User.where(login: login)
puts "User count with this login: #{users.count}"
