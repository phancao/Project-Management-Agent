# Setup user fully (Create/Update + Token)
email = 'cao.phan@galaxytechnology.vn'
login = 'cao.phan'
password = 'OpenProject123!'

puts "Checking user #{email}..."
user = User.find_by(mail: email)

if user.nil?
  puts "User not found. Creating..."
  user = User.new(mail: email, login: login, firstname: 'Cao', lastname: 'Phan', admin: true, language: 'en', status: 1) # status 1 = active
  user.password = password
  user.password_confirmation = password
  
  if user.save
    puts "User created successfully (ID: #{user.id})."
  else
    puts "Failed to create user: #{user.errors.full_messages.join(', ')}"
    # Try finding by login if mail failed?
    user_by_login = User.find_by(login: login)
    if user_by_login
       puts "User with login #{login} exists. Updating that one..."
       user = user_by_login
       user.mail = email
       user.password = password
       user.password_confirmation = password
       user.save!
    else
       exit 1
    end
  end
else
  puts "User exists (ID: #{user.id}). Updating password..."
  user.password = password
  user.password_confirmation = password
  user.firstname = 'Cao' if user.firstname.blank?
  user.lastname = 'Phan' if user.lastname.blank?
  user.admin = true # Make admin to be safe
  
  if user.save
    puts "User updated successfully."
  else
    puts "Failed to update user: #{user.errors.full_messages.join(', ')}"
  end
end

# Activate user if needed
if user.status != 1
  user.status = 1
  user.save(validate: false)
  puts "User activated."
end

# Generate Token
puts "Generating API token..."
# Create new token
token = Token::API.create(user: user)
if token.persisted?
  puts "API_TOKEN_RESULT: #{token.plain_value}"
else
  # If creation fails, maybe limit reached?
  # Try to delete old ones
  puts "Token creation failed (#{token.errors.full_messages}). Cleaning old tokens..."
  Token::API.where(user_id: user.id).destroy_all
  token = Token::API.create(user: user)
  if token.persisted?
      puts "API_TOKEN_RESULT: #{token.plain_value}"
  else
      puts "Failed to generate token again: #{token.errors.full_messages.join(', ')}"
  end
end
