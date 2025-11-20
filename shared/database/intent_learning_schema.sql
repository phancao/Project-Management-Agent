-- Self-Learning Intent Classification Schema
-- This schema tracks intent classification performance and learns from user feedback

-- Intent classifications history (track all classifications)
CREATE TABLE intent_classifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES conversation_sessions(id),
    message TEXT NOT NULL,
    classified_intent VARCHAR(50) NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    was_correct BOOLEAN DEFAULT NULL, -- NULL = unknown, TRUE = correct, FALSE = incorrect
    user_corrected_intent VARCHAR(50), -- If incorrect, what was the correct intent
    conversation_history JSONB, -- Context at time of classification
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Intent feedback from users
CREATE TABLE intent_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    classification_id UUID REFERENCES intent_classifications(id),
    feedback_type VARCHAR(20) NOT NULL, -- 'correction', 'confirmation', 'improvement'
    original_message TEXT,
    suggested_intent VARCHAR(50),
    user_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Intent success metrics (aggregated)
CREATE TABLE intent_metrics (
    intent_type VARCHAR(50) PRIMARY KEY,
    total_classifications INTEGER DEFAULT 0,
    correct_classifications INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    average_confidence FLOAT DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Common patterns that users use for intents (learned patterns)
CREATE TABLE learned_intent_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    intent_type VARCHAR(50) NOT NULL,
    pattern_text TEXT NOT NULL,
    success_count INTEGER DEFAULT 1, -- How many times this pattern worked
    failure_count INTEGER DEFAULT 0,
    pattern_type VARCHAR(20) DEFAULT 'keyword', -- 'keyword', 'phrase', 'context'
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_intent_classifications_session ON intent_classifications(session_id);
CREATE INDEX idx_intent_classifications_intent ON intent_classifications(classified_intent);
CREATE INDEX idx_intent_classifications_correct ON intent_classifications(was_correct);
CREATE INDEX idx_learned_patterns_intent ON learned_intent_patterns(intent_type);
CREATE INDEX idx_learned_patterns_confidence ON learned_intent_patterns(confidence);

