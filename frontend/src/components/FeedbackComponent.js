import React, { useState, useEffect } from 'react';
import axios from 'axios';

const FeedbackComponent = () => {
    const [feedbacks, setFeedbacks] = useState([]); // Store all feedbacks
    const [displayedFeedbacks, setDisplayedFeedbacks] = useState([]); // Store feedbacks to be displayed
    const [searchFeedbackId, setSearchFeedbackId] = useState(''); // Search ID
    const [newFeedback, setNewFeedback] = useState({ name: '', email: '', text: '' }); // New feedback form state
    const [formError, setFormError] = useState(null); // Error for feedback form

    // Fetch all feedbacks initially
    useEffect(() => {
        axios.get(`${process.env.REACT_APP_API_URL}/admin/feedback/`)
            .then(response => {
                setFeedbacks(response.data);
                setDisplayedFeedbacks(response.data);
            })
            .catch(error => console.error('Error:', error));
    }, []);

    // Update displayed feedbacks based on search input
    useEffect(() => {
        if (searchFeedbackId) {
            const foundFeedback = feedbacks.filter(feedback => feedback.feedback_id.toString() === searchFeedbackId.trim());
            setDisplayedFeedbacks(foundFeedback);
        } else {
            setDisplayedFeedbacks(feedbacks);
        }
    }, [searchFeedbackId, feedbacks]);

    const fetchFeedbacks = async () => {
        try {
            const response = await axios.get(`${process.env.REACT_APP_API_URL}/admin/feedback/`);
            if (response.status === 200) {
                setFeedbacks(response.data); // Update the feedbacks state with the fetched data
            } else {
                // Handle non-successful status codes
                setFormError('Error occurred while fetching feedbacks.');
            }
        } catch (error) {
            // Handle errors from the server
            setFormError('Error occurred while fetching feedbacks.');
        }
    };

    // Handle input change for new feedback
    const handleInputChange = (event) => {
        const { name, value } = event.target;
        setNewFeedback({ ...newFeedback, [name]: value });
    };

    // Handle adding new feedback
    const handleFeedbackSubmit = (event) => {
        event.preventDefault();
        setFormError(null); // Resetting any previous errors

        axios.post(`${process.env.REACT_APP_API_URL}/feedback/`, newFeedback)
            .then(response => {
                if (response.status === 200 || response.status === 201) {
                    setNewFeedback({ name: '', email: '', text: '' }); // Reset form fields
                    fetchFeedbacks(); // Fetch all feedbacks again to update the list
                } else {
                    // Handle non-successful status codes
                    setFormError('Feedback submission was not successful.');
                }
            })
            .catch(error => {
                // Handle errors from the server
                setFormError('Error occurred while adding feedback: ' + error.message);
            });
    };

    // Search input change handler
    const handleSearchInputChange = (event) => {
        setSearchFeedbackId(event.target.value);
    };

    return (
    <div className="feedback-section">
        {/* Feedback List */}
        <div className="feedback-list">
            <h3>Feedbacks</h3>
            <ol className="feedback-items" start={displayedFeedbacks.length > 0 ? displayedFeedbacks[0].feedback_id : 1}>
                {displayedFeedbacks.map(feedback => (
                    <li key={feedback.feedback_id} className="feedback-item">
                        <p>Name: {feedback.name}</p>
                        <p>Email: {feedback.email}</p>
                        <p>Text: {feedback.text}</p>
                        <p>Submission Date: {feedback.submission_date}</p>
                        {/*<p>Is Deleted: {feedback.isDeleted ? 'Yes' : 'No'}</p>*/}
                        <p>Actioned By: {feedback.actioned_by || 'N/A'}</p>
                        <p>Action Date: {feedback.action_date || 'N/A'}</p>
                        <p>Action Comment: {feedback.action_comment || 'N/A'}</p>
                    </li>
                ))}
            </ol>
        </div>

        {/* Feedback Form */}
        <h3>Add New Feedback</h3>
            <form onSubmit={handleFeedbackSubmit} className="feedback-form">
                <div className="feedback-form-group">
                    <label htmlFor="name" className="feedback-label">Name: </label>
                    <input
                        id="name"
                        type="text"
                        name="name"
                        value={newFeedback.name}
                        onChange={handleInputChange}
                        className="feedback-input"
                    />
                </div>
                <div className="feedback-form-group">
                    <p><label htmlFor="email" className="feedback-label">Email: </label>
                    <input
                        id="email"
                        type="email"
                        name="email"
                        value={newFeedback.email}
                        onChange={handleInputChange}
                        className="feedback-input"
                    /></p>
                </div>
                <div className="feedback-form-group">
                    <label htmlFor="text" className="feedback-label">Text: </label>
                    <textarea
                        id="text"
                        name="text"
                        value={newFeedback.text}
                        onChange={handleInputChange}
                        className="feedback-textarea"
                    />
                </div>
                <p></p>
                <button type="submit" className="feedback-submit-btn">Add Feedback</button>
                <p></p>
        </form>

        {/* Feedback Search */}
        <h3>Search Feedback by ID</h3>
        <div className="feedback-search">
            <label>Feedback ID: </label>
            <input
                type="text"
                value={searchFeedbackId}
                onChange={handleSearchInputChange}
                className="feedback-search-input"
            />
        </div>

        {/* Display form error, if any */}
        {formError && <p className="error-message">{formError}</p>}
    </div>
    );
};

export default FeedbackComponent;
