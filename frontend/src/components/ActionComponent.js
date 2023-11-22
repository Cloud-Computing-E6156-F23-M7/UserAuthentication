import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ActionComponent = () => {
    const [actions, setActions] = useState([]);
    const [newAction, setNewAction] = useState({ adminId: '', feedbackId: '', comment: '' });
    const [updateAction, setUpdateAction] = useState({ actionId: '', comment: '' });
    const [searchActionId, setSearchActionId] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        fetchActions();
    }, []);

    useEffect(() => {
        if (searchActionId) {
            const foundAction = actions.filter(action => action.action_id.toString() === searchActionId);
            setActions(foundAction);
        } else {
            fetchActions();
        }
    }, [searchActionId, actions]);

    // Function to fetch all actions
    const fetchActions = () => {
        axios.get(`${process.env.REACT_APP_API_URL}/admin/action/`)
            .then(response => {
                setActions(response.data);
                setError(null);
            })
            .catch(error => {
                console.error('Error fetching actions:', error);
                setError('Failed to fetch actions');
            });
    };
    const handleInputChange = (event, type) => {
        const { name, value } = event.target;
        if (type === 'new') {
            setNewAction({ ...newAction, [name]: value });
        } else if (type === 'update') {
            setUpdateAction({ ...updateAction, [name]: value });
        }
    };

    const handleAddAction = (event) => {
    event.preventDefault();
    console.log('Attempting to add action:', newAction); // Debugging
    axios.post(`${process.env.REACT_APP_API_URL}/admin/${newAction.adminId}/feedback/${newAction.feedbackId}/`,
        { comment: newAction.comment })
        .then(response => {
            console.log('Add action response:', response); // Debugging
            fetchActions();
            setNewAction({ adminId: '', feedbackId: '', comment: '' });
        })
        .catch(error => {
            console.error('Error adding action:', error);
            setError('Failed to add action');
            console.log('Failed request details:', error.response); // Additional debugging
        });
    };


    const handleUpdateAction = (event) => {
        event.preventDefault();
        axios.put(`${process.env.REACT_APP_API_URL}/admin/action/${updateAction.actionId}/`, { comment: updateAction.comment })
        .then(() => {
            fetchActions(); // Refresh the actions list
            setUpdateAction({ actionId: '', comment: '' }); // Reset the form
        })
        .catch(error => {
            console.error('Error updating action:', error);
            setError('Failed to update action');
        });
};

    const handleDeleteAction = (actionId) => {
        axios.delete(`${process.env.REACT_APP_API_URL}/admin/action/${actionId}/`)
        .then(() => {
            fetchActions(); // Refresh the actions list
        })
        .catch(error => {
            console.error('Error deleting action:', error);
            setError('Failed to delete action');
        });
};

    const handleSearchInputChange = (event) => {
        setSearchActionId(event.target.value);
    };

    return (
        <div>
            <h3>Actions</h3>
            {error && <p className="error">{error}</p>}

            {/* Actions List */}
            <div className="actions-list">
                {actions.map(action => (
                    <div key={action.action_id} className="action-item">
                        <p>Action ID: {action.action_id}</p>
                        <p>Admin ID: {action.admin_id}</p>
                        <p>Feedback ID: {action.feedback_id}</p>
                        <p>Comment: {action.action_comment}</p>
                        <p>Action Date: {action.action_date}</p>
                        <button onClick={() => handleDeleteAction(action.action_id)} className="btn-delete">Delete Action</button>
                    </div>
                ))}
            </div>

            <h3>Add Action</h3>
            {/* Form to Add New Action */}
            <form onSubmit={handleAddAction} className="action-form">
                <div className="form-group">
                    <label htmlFor="adminId">Admin ID:</label>
                    <input type="text" id="adminId" name="adminId" value={newAction.adminId}
                           onChange={(e) => handleInputChange(e, 'new')} />
                </div>
                <div className="form-group">
                    <label htmlFor="feedbackId">Feedback ID:</label>
                    <input type="text" id="feedbackId" name="feedbackId" value={newAction.feedbackId}
                           onChange={(e) => handleInputChange(e, 'new')} />
                </div>
                <div className="form-group">
                    <label htmlFor="comment">Comment:</label>
                    <textarea id="comment" name="comment" value={newAction.comment}
                              onChange={(e) => handleInputChange(e, 'new')}></textarea>
                </div>
                <button type="submit" className="btn-submit">Add Action</button>
            </form>

            <h3>Update Action</h3>
            {/* Form to Update an Action */}
            <form onSubmit={handleUpdateAction} className="action-form">
                <div className="form-group">
                    <label htmlFor="updateActionId">Action ID:</label>
                    <input type="text" id="updateActionId" name="actionId" value={updateAction.actionId}
                           onChange={(e) => handleInputChange(e, 'update')} />
                </div>
                <div className="form-group">
                    <label htmlFor="updateComment">New Comment:</label>
                    <textarea id="updateComment" name="comment" value={updateAction.comment}
                              onChange={(e) => handleInputChange(e, 'update')}></textarea>
                </div>
                <button type="submit" className="btn-submit">Update Action</button>
            </form>

            <h3>Search Action by ID</h3>
            {/* Input for Action ID Search */}
            <div className="search-action">
                <label htmlFor="searchActionId">Search Action ID:</label>
                <input
                    type="text"
                    id="searchActionId"
                    value={searchActionId}
                    onChange={handleSearchInputChange}
                />
            </div>
        </div>
    );
};

export default ActionComponent;

