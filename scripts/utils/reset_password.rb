# Reset password for user
email = 'cao.phan@galaxytechnology.vn'
password = 'OpenProject123!'

puts "Finding user #{email}..."
user = User.find_by(mail: email)

if user.nil?
  puts "User not found!"
  exit 1
end

puts "User found: #{user.login} (ID: #{user.id})"

# Force password update
user.password = password
user.password_confirmation = password
user.force_password_change = false
user.first_login = false
# user.failed_login_count = 0 # In case they are locked out?

if user.save
  puts "Password updated successfully."
else
  puts "Failed to update password: #{user.errors.full_messages.join(', ')}"
  exit 1
end
