# Requirements Document

## Introduction

Orientation Mali is a school orientation application built with the Strands Agents SDK for Python. It helps Malian students who are taking the Diplôme d'Études Fondamentales (DEF) or the Baccalauréat (BAC) exams make informed decisions about their study choices. The application guides students through a profiling questionnaire, analyzes their responses using AI agents powered by Amazon Nova Pro models, and provides personalized recommendations including suitable majors, training programs, schools/universities, and potential career paths. All user-facing content is presented in French.

## Glossary

- **Application**: The Orientation Mali web application that students interact with
- **Student**: A Malian student preparing for the DEF or BAC exam who uses the Application
- **Profiling_Questionnaire**: A form of ten simple questions designed to assess a student's interests, strengths, and aspirations
- **Profile_Agent**: An AI agent built with Strands Agents SDK that analyzes questionnaire responses and derives a student profile
- **Recommendation_Agent**: An AI agent built with Strands Agents SDK that uses the student profile to generate orientation recommendations
- **Student_Profile**: A structured representation of the student's interests, academic strengths, personality traits, and career aspirations derived from questionnaire responses
- **Recommendation_Set**: A collection of personalized suggestions including majors, training programs, schools/universities, and potential jobs
- **DEF**: Diplôme d'Études Fondamentales, equivalent to middle school completion in Mali
- **BAC**: Baccalauréat, equivalent to high school diploma in Mali
- **Amazon_Nova_Pro**: The foundation model from Amazon used by the AI agents for inference
- **Strands_Agents_SDK**: The Python SDK used to build and orchestrate the AI agents
- **Major**: An academic specialization or series (e.g., Sciences Exactes, Sciences Biologiques, Lettres) available to students after the DEF or BAC

## Requirements

### Requirement 1: Display Profiling Questionnaire

**User Story:** As a student, I want to see a simple questionnaire when I open the app, so that I can provide information about my interests and goals.

#### Acceptance Criteria

1. WHEN a Student opens the Application, THE Application SHALL display the Profiling_Questionnaire containing exactly ten questions
2. THE Application SHALL present all Profiling_Questionnaire questions in French
3. THE Application SHALL present questions that assess the Student's academic interests, strengths, preferred subjects, and career aspirations
4. WHEN the Student has not yet completed the Profiling_Questionnaire, THE Application SHALL allow the Student to select their exam type (DEF or BAC)

### Requirement 2: Submit Questionnaire Responses

**User Story:** As a student, I want to submit my questionnaire responses, so that the system can analyze my profile.

#### Acceptance Criteria

1. WHEN the Student completes all ten questions of the Profiling_Questionnaire, THE Application SHALL enable a submission button
2. WHEN the Student submits the Profiling_Questionnaire with incomplete responses, THE Application SHALL display a French-language validation message indicating which questions remain unanswered
3. WHEN the Student submits the completed Profiling_Questionnaire, THE Application SHALL send the responses to the Profile_Agent for analysis

### Requirement 3: Analyze Student Profile

**User Story:** As a student, I want the system to analyze my responses, so that it can understand my academic profile and preferences.

#### Acceptance Criteria

1. WHEN the Profile_Agent receives the Profiling_Questionnaire responses, THE Profile_Agent SHALL analyze the responses and generate a Student_Profile
2. THE Profile_Agent SHALL use the Amazon_Nova_Pro model for inference via the Strands_Agents_SDK
3. WHEN the Profile_Agent completes the analysis, THE Profile_Agent SHALL produce a Student_Profile containing the Student's identified strengths, interests, personality traits, and academic inclinations
4. IF the Profile_Agent fails to generate a Student_Profile, THEN THE Application SHALL display a French-language error message and offer the Student the option to retry

### Requirement 4: Generate Recommendations

**User Story:** As a student, I want to receive personalized recommendations based on my profile, so that I can make informed decisions about my academic future.

#### Acceptance Criteria

1. WHEN the Recommendation_Agent receives a Student_Profile, THE Recommendation_Agent SHALL generate a Recommendation_Set
2. THE Recommendation_Agent SHALL use the Amazon_Nova_Pro model for inference via the Strands_Agents_SDK
3. THE Recommendation_Set SHALL include at least one recommended Major appropriate for the Student's exam type (DEF or BAC)
4. THE Recommendation_Set SHALL include at least one training program aligned with the recommended Major
5. THE Recommendation_Set SHALL include at least one school or university in Mali that offers the recommended Major
6. THE Recommendation_Set SHALL include at least one potential job or career path associated with the recommended Major
7. IF the Recommendation_Agent fails to generate a Recommendation_Set, THEN THE Application SHALL display a French-language error message and offer the Student the option to retry

### Requirement 5: Display Recommendations

**User Story:** As a student, I want to view my recommendations in a clear format, so that I can explore my options easily.

#### Acceptance Criteria

1. WHEN the Recommendation_Agent completes generating the Recommendation_Set, THE Application SHALL display the recommendations to the Student in French
2. THE Application SHALL organize the Recommendation_Set into distinct sections: recommended majors, training programs, schools/universities, and potential jobs
3. WHEN a school or university is listed in the Recommendation_Set, THE Application SHALL provide a navigable link to the school's webpage when available
4. THE Application SHALL display the Student_Profile summary alongside the Recommendation_Set so the Student understands the basis for the recommendations

### Requirement 6: French Language Interface

**User Story:** As a Malian student, I want the entire application to be in French, so that I can use it comfortably in my language of instruction.

#### Acceptance Criteria

1. THE Application SHALL display all user interface elements in French
2. THE Application SHALL display all agent-generated content (Student_Profile and Recommendation_Set) in French
3. THE Application SHALL display all error messages and validation messages in French
4. THE Profile_Agent SHALL generate the Student_Profile in French
5. THE Recommendation_Agent SHALL generate the Recommendation_Set in French

### Requirement 7: Agent Architecture

**User Story:** As a developer, I want the agents to be built with the Strands Agents SDK using Amazon Nova Pro, so that the system leverages reliable AI infrastructure.

#### Acceptance Criteria

1. THE Profile_Agent SHALL be implemented using the Strands_Agents_SDK for Python
2. THE Recommendation_Agent SHALL be implemented using the Strands_Agents_SDK for Python
3. THE Profile_Agent SHALL use Amazon_Nova_Pro as its foundation model
4. THE Recommendation_Agent SHALL use Amazon_Nova_Pro as its foundation model
5. WHEN the Profile_Agent completes generating the Student_Profile, THE Profile_Agent SHALL pass the Student_Profile to the Recommendation_Agent for further processing

### Requirement 8: Malian Education Context

**User Story:** As a Malian student, I want the recommendations to reflect the Malian education system, so that the suggestions are relevant to my actual options.

#### Acceptance Criteria

1. WHEN the Student selects DEF as their exam type, THE Recommendation_Agent SHALL provide recommendations relevant to post-DEF academic paths in Mali (e.g., lycée series selection, technical training)
2. WHEN the Student selects BAC as their exam type, THE Recommendation_Agent SHALL provide recommendations relevant to post-BAC academic paths in Mali (e.g., university programs, grandes écoles, professional training)
3. THE Recommendation_Agent SHALL reference Malian educational institutions and programs in the Recommendation_Set
4. THE Recommendation_Agent SHALL consider the available BAC series in Mali (Sciences Exactes, Sciences Biologiques, Lettres, Sciences Humaines, Sciences Économiques) when generating recommendations for DEF students
