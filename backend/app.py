import os
from flask import Flask, jsonify, request
from database import db
from agent_graph import app_graph
from langchain_core.messages import HumanMessage
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app) # Enable CORS for all routes
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    @app.route('/health')
    def health():
        try:
            # Check database connection
            db.session.execute(db.text('SELECT 1'))
            return jsonify({'status': 'healthy', 'database': 'connected'})
        except Exception as e:
            return jsonify({'status': 'unhealthy', 'database': str(e)}), 500

    @app.route('/api/run_workflow', methods=['POST'])
    def run_workflow():
        data = request.json
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "plan": [],
            "current_step": 0,
            "results": {}
        }
        
        # Invoke the graph
        final_state = app_graph.invoke(initial_state)
        
        # Extract messages/results
        messages = [m.content for m in final_state['messages']]
        
        return jsonify({
            'status': 'success',
            'plan': final_state.get('plan'),
            'results': final_state.get('results'),
            'messages': messages
        })

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
